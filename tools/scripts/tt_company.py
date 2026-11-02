import datetime as dt, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt, tt_docs
from config import api_path
# P6 fetch (needs TAPETIDE_TOKEN): caches every Tapetide answer P7 needs in data/companies/<SYM>/api/ and downloads
# the documents in process/p6_fetch.md step 3 into data/companies/<SYM>/<FYyyQn>/, recorded in index.json.
# The filings list is always refreshed; the rest only when the list shows a filing since the last fetch (or --refresh).
#   python tools/scripts/tt_company.py SYM [--refresh]
sym = sys.argv[1]
force = '--refresh' in sys.argv
p = tt.sym_path(sym)
today = dt.date.today()
since3 = (today - dt.timedelta(days=3 * 365)).isoformat()
calls0 = sum(1 for _ in open(tt.CALL_LOG, encoding='utf-8')) if os.path.exists(tt.CALL_LOG) else 0
GOV = re.compile(r'auditor|preferential|qip|warrant|reg(ulation)?\.? ?(7|29|31)|sast|pledge|encumbr|credit rating|rating|sebi|'
                 r'show cause|penalt|fine|litigation|court|tribunal|nclt|related party|resign|fraud|forensic|default|'
                 r'insolvency|order|contract|acquisition|merger|demerger|buyback|rights issue|allotment', re.I)
GOV_CATS = {'credit_rating', 'capital_raise', 'insider_takeover', 'management_change', 'insolvency', 'acquisition',
            'orders_contracts', 'corporate_action', 'shareholder_meeting', 'clarification'}
try:
    old = tt.cached(api_path(sym, 'filings'))
    last = old['fetched_at'][:10] if old else None
    fl = tt.fetch(sym, 'filings', f'/v1/stocks/{p}/filings', {'from': since3, 'limit': 200}, all_pages=True, refresh=True)
    filings = tt_docs.items(fl)
    newer = force or not last or any(str(tt_docs.f_date(x) or '') >= last for x in filings)
    age = None if newer else 9999
    tt.fetch(sym, 'financials', f'/v1/stocks/{p}/financials', {'periods': 40}, max_age_days=age, refresh=newer)
    tt.fetch(sym, 'shareholding', f'/v1/stocks/{p}/shareholding', refresh=newer, max_age_days=age)
    tt.fetch(sym, 'pledge', f'/v1/stocks/{p}/promoter-pledge', {'limit': 100, 'order': 'desc'}, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'pledge_events', f'/v1/stocks/{p}/promoter-pledge/events', {'from': since3, 'limit': 200}, all_pages=True, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'insider', f'/v1/stocks/{p}/insider-trades', {'from': since3, 'limit': 200}, all_pages=True, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'sast', f'/v1/stocks/{p}/sast-disclosures', {'from': since3, 'limit': 200}, all_pages=True, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'deals', f'/v1/stocks/{p}/bulk-block-deals', {'from': since3, 'limit': 200}, all_pages=True, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'credit_ratings', f'/v1/stocks/{p}/credit-ratings', {'limit': 200}, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'corporate_actions', f'/v1/stocks/{p}/corporate-actions', {'limit': 200, 'order': 'desc'}, refresh=newer, max_age_days=age)
    tt.fetch(sym, 'profile', f'/v1/stocks/{p}', {'include': 'peers'}, refresh=newer, max_age_days=age)
    docs = tt.fetch(sym, 'documents', f'/v1/stocks/{p}/documents', {'limit': 50}, refresh=newer, max_age_days=age)
except tt.QuotaExceeded as e:
    sys.exit(f'QUOTA EXCEEDED while fetching {sym}: nothing downloaded; re-run after the reset. {e}')

idx = tt_docs.load_index(sym)
n = 0
D = tt_docs.items(docs)
for typ, keep, pdf in (('concall', 6, False), ('presentation', 4, False), ('annual_report', 3, True), ('drhp', 1, True), ('rhp', 1, True)):
    for d in [d for d in D if d.get('doc_type') == typ][:keep]:
        n += tt_docs.get_parsed_doc(sym, idx, d, with_pdf=pdf)
# filings: results (last 8), governance and business events (3 years), as PDFs with text
res, gov = [], []
for x in filings:
    cat, title = (x.get('category') or x.get('doc_type') or ''), (x.get('title') or x.get('subject') or '')
    if cat in ('financial_results', 'result') or re.search(r'financial results', title, re.I):
        res.append(x)
    elif cat in GOV_CATS or GOV.search(title):
        gov.append(x)
for x in res[:8] + gov[:80]:
    d, url = tt_docs.f_date(x), tt_docs.f_url(x)
    if not d or not url:
        continue
    is_res = x in res
    q = tt_docs.reported_quarter(d) if is_res else tt_docs.fy_quarter(d)
    ident = re.sub(r'\W', '', (url.split('Pname=')[-1] if 'Pname=' in url else url.rsplit('/', 1)[-1]))[:40]
    fname = f"{'results' if is_res else 'filing'}_{d.isoformat()}_{ident}.pdf".replace('pdfpdf', 'pdf')
    src = 'bse' if 'bseindia' in url else 'nse' if 'nseindia' in url else 'tapetide'
    n += bool(tt_docs.get(sym, idx, url, q, fname, 'results' if is_res else 'filing:' + (x.get('category') or 'other'),
                          x.get('title'), d, src, ident, text=True))
idx['last_fetched'] = today.isoformat()
tt_docs.save_index(sym, idx)
calls1 = sum(1 for _ in open(tt.CALL_LOG, encoding='utf-8')) if os.path.exists(tt.CALL_LOG) else 0
print(f'{sym}: Tapetide data {"refreshed" if newer else "unchanged (cache kept)"}; filings listed {len(filings)} '
      f'(results {len(res)}, governance/business {len(gov)}); files downloaded {n}; missing {len(idx["missing"])}; '
      f'Tapetide calls used {calls1 - calls0 - (1 if calls0 == 0 and calls1 else 0)}')
