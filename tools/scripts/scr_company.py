import asyncio, datetime as dt, json, os, re, sys
# P4/P6: one company's screener.in data into data/companies/<SYM>/scr/, with no model tokens and no login: the
# screener-mcp library in public mode reads screener's public company page (every year and quarter on it, not the
# MCP tools' 8-quarter cut) and NSE's feeds: announcements, insider trades, promoter pledge (latest), SAST Reg 29 disclosures,
# corporate actions and the shareholding-pattern list (about 26 quarters), plus promoter holding and pledge per quarter read
# from the last 12 filed shareholding-pattern XBRLs (scr/shp_history.json). Run it through uvx (the library isn't installed):
#   uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py SYM [--days 1100] [--only quarterly,shareholding]
# Writes {fetched_at (IST), via: "screener-public", tool, args, warnings, data} per item, the same envelope as scr_save.py.
os.environ.setdefault('SCREENER_MIN_INTERVAL', '1.2')  # fewer 429 cooldowns at the same throughput (tools/tools.md)
from screener_mcp.core.company_page import fetch_company_page
from screener_mcp.parsers.company import parse_quarterly_results
from screener_mcp.tools import company_tools as ct
from screener_mcp.tools.announcements import _fetch_filtered
from screener_mcp.tools.documents import get_document_list
from screener_mcp.tools.insider_trading import get_insider_trading
from screener_mcp.core.nse_client import get_nse_client
from bs4 import BeautifulSoup

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
sym = sys.argv[1]
days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 1100
only = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
out_dir = os.path.join('data', 'companies', sym, 'scr')
os.makedirs(out_dir, exist_ok=True)

def save(name, tool, args, data, warnings=None):
    env = {'fetched_at': dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'screener-public', 'tool': tool,
           'args': args, 'warnings': warnings or [], 'data': data}
    json.dump(env, open(os.path.join(out_dir, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def result(r):
    return r.data, list(r.warnings or []) + ([r.reason] if getattr(r, 'reason', None) else [])

async def main():
    done, failed = [], []

    async def item(name, fn):
        if only and name not in only:
            return
        try:
            await fn()
            done.append(name)
        except Exception as e:  # one failed item doesn't stop the rest
            failed.append(f'{name}: {type(e).__name__}: {e}'[:300])

    pages = {}

    async def page(ft):
        if ft not in pages:
            pages[ft] = await fetch_company_page(sym, ft)
        return pages[ft]

    async def statements():
        for ft in ('consolidated', 'standalone'):
            p = await page(ft)
            if p.financial_type != ft:  # no consolidated page: the site served standalone
                continue
            for st in ('profit_loss', 'balance_sheet', 'cash_flow', 'ratios'):
                data, missing, warns, reason = await ct.statement_data(p, st, years=12)
                save(st if ft == 'consolidated' else f'{st}_standalone', 'get_financials',
                     {'symbol': sym, 'statement': st, 'financial_type': ft, 'years': 12}, data,
                     list(warns or []) + ([reason] if reason else []))

    async def quarterly():
        for ft in ('consolidated', 'standalone'):
            p = await page(ft)
            if p.financial_type != ft:
                continue
            t = parse_quarterly_results(p.html)
            q = t.get('years', [])
            data = {'symbol': sym, 'financial_type': ft, 'units': '₹ Cr (OPM % and EPS as labelled)', 'quarters': q,
                    'rows': ct._table_rows(t.get('rows', []), 'label', len(q)) if q else []}
            save('quarterly' if ft == 'consolidated' else 'quarterly_standalone', 'get_quarterly_results',
                 {'symbol': sym, 'financial_type': ft, 'all_quarters': True}, data)

    async def shareholding():
        data, missing, reason = ct.shareholding_data(await page('standalone'), n=99)
        save('shareholding', 'get_shareholding_pattern', {'symbol': sym, 'all_quarters': True}, data, [reason] if reason else [])

    async def peers():
        data, missing, reason = await ct.peers_data(await page('consolidated'))
        save('peers', 'get_peer_comparison', {'symbol': sym}, data, [reason] if reason else [])

    async def overview():
        data, warns = result(await ct.get_company_overview(sym))
        save('overview', 'get_company_overview', {'symbol': sym}, data, warns)

    async def documents():
        data, warns = result(await get_document_list(sym))
        save('documents', 'get_document_list', {'symbol': sym}, data, warns)

    async def announcements():
        nse_symbol, rows, total, d, warns, meta = await _fetch_filtered(sym, 'all', days)
        save('announcements', 'get_company_announcements', {'symbol': sym, 'category': 'all', 'days': d, 'uncapped': True},
             {'symbol': nse_symbol, 'days': d, 'total_announcements_fetched': total, 'matches': len(rows), 'announcements': rows}, warns)

    async def insider():
        data, warns = result(await get_insider_trading(sym, days))
        save('insider', 'get_insider_trading', {'symbol': sym, 'days': days}, data, warns)

    async def credit_ratings():  # the rating agencies' rationale letters listed on screener's company page
        soup = BeautifulSoup((await page('consolidated')).html, 'lxml')
        box = soup.find('div', class_='credit-ratings')
        links = [{'title': ' '.join(a.get_text(' ', strip=True).split()), 'url': a.get('href')}
                 for a in (box.find_all('a') if box else []) if a.get('href', '').startswith('http')]
        save('credit_ratings', 'company_page', {'symbol': sym, 'section': 'credit-ratings'}, {'symbol': sym, 'ratings': links})

    async def nse_items():  # NSE feeds the MCP tools don't expose; SME companies sit under index=sme
        nse = await get_nse_client()
        for name, path, extra in (('pledge_nse', '/api/corporate-pledgedata', {}),
                                  ('sast', '/api/corporate-sast-reg29', {}),
                                  ('corporate_actions', '/api/corporates-corporateActions', {}),
                                  ('shareholding_nse', '/api/corporate-share-holdings-master', {})):
            rows, seen, used = [], set(), []
            for idx in ('equities', 'sme'):  # a company that moved boards has rows under both
                r = await nse.get_json(path, {'index': idx, 'symbol': sym, **extra})
                for x in (r.get('data', []) if isinstance(r, dict) else (r or [])):
                    k = json.dumps(x, sort_keys=True, default=str)
                    if k not in seen:
                        seen.add(k)
                        rows.append(dict(x, _index=idx))
                        used.append(idx)
            save(name, 'nse:' + path, {'symbol': sym, 'index': sorted(set(used)), **extra}, {'symbol': sym, 'rows': rows})
            if name == 'shareholding_nse':
                await shp_history(nse, rows)

    async def shp_history(nse, rows, n=12):
        """Promoter holding and pledge per quarter, read from each filed shareholding-pattern XBRL (last n quarters)."""
        def val(t, tag, ctx):
            m = re.search(r'<in-bse-shp:' + tag + r'(?=[\s/>])[^>]*contextRef="' + ctx + r'"[^>]*>([^<]*)<', t)
            return float(m.group(1)) if m and m.group(1).strip() else None
        out, seen = [], set()
        for r in rows:
            if not r.get('xbrl') or r.get('date') in seen or len(out) >= n:
                continue
            seen.add(r.get('date'))
            t = (await nse._client.get(r['xbrl'])).text
            prom, total = val(t, 'NumberOfShares', 'ShareholdingOfPromoterAndPromoterGroup_ContextI'), val(t, 'NumberOfShares', 'ShareholdingPattern_ContextI')
            pl_pct = val(t, 'EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares', 'ShareholdingOfPromoterAndPromoterGroup_ContextI')
            enc_pct = val(t, 'EncumberedSharesHeldAsPercentageOfTotalNumberOfShares', 'ShareholdingOfPromoterAndPromoterGroup_ContextI')
            flag = re.search(r'<in-bse-shp:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged(?=[\s/>])[^>]*>([^<]*)<', t)
            out.append({'quarter_end': r.get('date'), 'filed': r.get('submissionDate'), 'revised': r.get('revisedData'),
                        'total_shares': total, 'promoter_shares': prom,
                        'promoter_pct': round(prom / total * 100, 2) if prom is not None and total else None,
                        'pledged_pct_of_promoter': round(pl_pct * 100, 2) if pl_pct is not None else (0.0 if flag and flag.group(1) == 'false' else None),
                        'encumbered_pct_of_promoter': round(enc_pct * 100, 2) if enc_pct is not None else None,
                        'pledge_flag': flag.group(1) if flag else None, 'xbrl': r['xbrl']})
        save('shp_history', 'nse:shp_xbrl', {'symbol': sym, 'quarters': n}, {'symbol': sym, 'rows': out})

    for name, fn in (('statements', statements), ('quarterly', quarterly), ('shareholding', shareholding), ('peers', peers), ('overview', overview),
                     ('documents', documents), ('announcements', announcements), ('insider', insider),
                     ('credit_ratings', credit_ratings), ('nse', nse_items)):
        await item(name, fn)
    print(f'{sym}: saved {", ".join(done) or "nothing"} in {out_dir}' + (f'; FAILED: {"; ".join(failed)}' if failed else ''))
    if failed:
        sys.exit(2)

asyncio.run(main())
