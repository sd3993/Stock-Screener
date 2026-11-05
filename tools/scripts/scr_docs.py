import datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt_docs
# F7 downloads from the company's saved screener answers (run scr_company.py first): results filings (last 8),
# investor presentations and call transcripts (last 6 quarters), governance and business filings (3 years) from the
# NSE announcements; annual reports (last 3) and exchange-hosted transcripts from the document list. PDFs with text,
# into data/companies/<SYM>/<FYyyQn>/, recorded in index.json; nothing indexed is downloaded again.
#   python tools/scripts/scr_docs.py SYM
sym = sys.argv[1]
base = os.path.join('data', 'companies', sym, 'scr')
load = lambda n: (json.load(open(os.path.join(base, n + '.json'), encoding='utf-8'))['data']
                  if os.path.exists(os.path.join(base, n + '.json')) else {})
today = dt.date.today()
GOV = re.compile(r'auditor|preferential|qip|warrant|reg(ulation)?\.? ?(7|29|31)|sast|substantial acquisition|pledge|'
                 r'encumbr|credit rating|sebi|show cause|penalt|fine|litigation|court|tribunal|nclt|related party|resign|'
                 r'fraud|forensic|default|insolvency|order|contract|acquisition|merger|demerger|amalgamation|buyback|'
                 r'rights issue|allotment|change in (director|management|kmp)|cessation|appointment', re.I)

def nse(url):  # nsearchives.nseindia.com hangs for curl; archives.nseindia.com serves the same paths
    return url.replace('://nsearchives.nseindia.com/', '://archives.nseindia.com/')

def day(s):
    try:
        return dt.datetime.strptime(s[:11], '%d-%b-%Y').date()
    except (TypeError, ValueError):
        return tt_docs.parse_date(s)

idx = tt_docs.load_index(sym)
n, skipped = 0, []
res, calls, gov = [], [], []
for a in load('announcements').get('announcements', []):
    d, url = day(a.get('date')), a.get('url')
    if not d or not str(url).startswith('http'):  # exchange queries (volume/price moves) carry no file
        continue
    cat, nc, head = a.get('category') or '', a.get('nse_category') or '', a.get('headline') or ''
    if re.search(r'outcome of board meeting|financial result', nc, re.I) and re.search(r'financial result', head, re.I) \
            and not re.search(r'newspaper|intimation', nc + head, re.I):
        res.append((d, url, 'results', head))
    elif re.search(r'investor presentation|analysts?/institutional investor meet|con\.? ?call|transcript', nc + ' ' + head, re.I):
        if (today - d).days <= 550 and not re.search(r'intimation|schedule', head, re.I) or re.search(r'transcript', head, re.I):
            calls.append((d, url, 'earnings_call', head))
    elif cat in ('insider_trading', 'acquisition', 'fund_raise', 'credit_rating', 'buyback') or GOV.search(nc + ' ' + head):
        gov.append((d, url, 'filing:' + (cat or 'other'), head))
for d, url, typ, head in res[:8] + calls + gov[:120]:
    q = tt_docs.reported_quarter(d) if typ in ('results', 'earnings_call') else tt_docs.fy_quarter(d)
    ident = tt_docs.url_id(url)
    src = 'bse' if 'bseindia' in url else 'nse' if 'nseindia' in url else 'web'
    kind = typ.split(':')[0]
    n += bool(tt_docs.get(sym, idx, nse(url), q, f'{kind}_{d.isoformat()}_{ident}.pdf', typ, head[:120], d, src, ident, text=True))
docs = load('documents')
for r in docs.get('annual_reports', [])[:3]:
    url, y = r.get('url') or '', r.get('year')
    if not url or not y or not url.lower().endswith('.pdf'):
        skipped.append(f"annual report {y}: {url or 'no link'}")
        continue
    q = f'FY{int(y) % 100:02d}Q4'
    ident = tt_docs.url_id(url)
    n += bool(tt_docs.get(sym, idx, url, q, f'annual_report_FY{y}_{ident}.pdf', 'annual_report', f'FY{y}',
                          dt.date(int(y), 3, 31), 'bse' if 'bseindia' in url else 'web', ident, text=True))
for r in docs.get('earnings_calls', [])[:6]:
    url, d = r.get('url') or '', tt_docs.parse_date(r.get('quarter'))  # "Aug 2026": the call's month
    if not d or not re.search(r'bseindia|nseindia', url):
        skipped.append(f"transcript {r.get('quarter')}: not an exchange link ({url or 'none'})")
        continue
    ident = tt_docs.url_id(url)
    n += bool(tt_docs.get(sym, idx, nse(url), tt_docs.reported_quarter(d), f'transcript_{d.isoformat()}_{ident}.pdf',
                          'transcript', r.get('quarter'), d, 'bse' if 'bseindia' in url else 'nse', ident, text=True))
idx['last_fetched'] = today.isoformat()
tt_docs.save_index(sym, idx)
print(f'{sym}: announcements -> results {len(res)}, presentations/calls {len(calls)}, governance {len(gov)}; '
      f'files downloaded {n}; missing {len(idx["missing"])}; skipped {len(skipped)}')
for s in skipped:
    print('  skipped', s)
