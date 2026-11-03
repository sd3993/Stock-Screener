import asyncio, csv, datetime as dt, json, os, sys
# Multibagger study, step 1 (process/study_multibaggers/s1_universe.md): long price and valuation history per company from screener.in's public chart API
# (no login, no model tokens), back to about 2005: price and volume, P/E with the TTM EPS behind it, and market cap to
# sales with TTM sales (market cap = the ratio x sales). Saved as data/companies/<SYM>/scr/history.json; a company already
# saved is skipped unless --refresh. Input: symbols, or a CSV with columns sym and (optionally) screener_id.
#   uvx --from screener-mcp==0.5.0 python tools/scripts/mb_history.py SYM ... | --csv studies/multibaggers/universe.csv [--refresh]
from screener_mcp.client import get_client
from screener_mcp.core.company_page import fetch_company_page

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
QUERIES = {'price': 'Price-Volume', 'pe': 'Price to Earning-Median PE-EPS',
           'mcap_sales': 'Market Cap to Sales-Median Market Cap to Sales-Sales'}
a = sys.argv[1:]
refresh = '--refresh' in a
if '--csv' in a:
    todo = [(r['sym'], r.get('screener_id') or None) for r in csv.DictReader(open(a[a.index('--csv') + 1], encoding='utf-8'))]
else:
    todo = [(s, None) for s in a if not s.startswith('--')]

async def one(client, sym, cid):
    out = os.path.join('data', 'companies', sym, 'scr', 'history.json')
    if os.path.exists(out) and not refresh:
        return 'cached'
    if not cid:
        cid = (await fetch_company_page(sym, 'consolidated')).company_id
    series = {}
    for key, q in QUERIES.items():
        for consolidated in ('true', ''):  # consolidated where the company files it, else standalone
            r = await client.get_json(f'/api/company/{cid}/chart/', params={'q': q, 'days': 10000, 'consolidated': consolidated})
            ds = {d.get('metric') or d.get('label'): d.get('values') for d in (r or {}).get('datasets', [])}
            if any(v for v in ds.values()):
                series[key] = {'consolidated': bool(consolidated), 'datasets': ds}
                break
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({'fetched_at': dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'screener-public',
               'tool': 'chart', 'args': {'symbol': sym, 'company_id': cid, 'days': 10000}, 'data': series},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    return 'saved'

async def main():
    client = await get_client()
    counts, failed = {}, []
    for i, (sym, cid) in enumerate(todo, 1):
        try:
            k = await one(client, sym, cid)
            counts[k] = counts.get(k, 0) + 1
        except Exception as e:  # one company's failure doesn't stop the run; re-run to retry
            failed.append(f'{sym}: {type(e).__name__}: {e}'[:200])
        if i % 100 == 0:
            print(f'{i}/{len(todo)} {counts} failed {len(failed)}', flush=True)
    print(f'done {len(todo)}: {counts}; failed {len(failed)}')
    for f in failed[:50]:
        print('  ', f)

asyncio.run(main())
