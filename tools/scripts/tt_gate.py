import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt, tt_docs
from config import run_dir
# P4 pre-fetch (needs TAPETIDE_TOKEN): for each company in a gate batch, caches in data/companies/<SYM>/api/
# financials (all sections), shareholding, the 3-year filings list and the documents list (4+ calls; cached
# answers younger than 7 days are reused), then downloads the latest transcript and presentation filed in the
# last 12 months (or the latest annual report) as Markdown, free.
#   python tools/scripts/tt_gate.py --batch N      or      python tools/scripts/tt_gate.py SYM [SYM ...]
a = sys.argv[1:]
if a and a[0] == '--batch':
    syms = json.load(open(os.path.join(run_dir(), 'gate_batches.json'), encoding='utf-8'))['batches'][a[1]]
else:
    syms = a
today = dt.date.today()
since3 = (today - dt.timedelta(days=3 * 365)).isoformat()
calls0 = sum(1 for _ in open(tt.CALL_LOG, encoding='utf-8')) if os.path.exists(tt.CALL_LOG) else 0

def gate_fetch(sym):
    p = tt.sym_path(sym)
    tt.fetch(sym, 'financials', f'/v1/stocks/{p}/financials', {'periods': 40}, max_age_days=7)
    tt.fetch(sym, 'shareholding', f'/v1/stocks/{p}/shareholding', max_age_days=7)
    tt.fetch(sym, 'filings', f'/v1/stocks/{p}/filings', {'from': since3, 'limit': 200}, all_pages=True, max_age_days=7)
    docs = tt.fetch(sym, 'documents', f'/v1/stocks/{p}/documents', {'limit': 50}, max_age_days=7)
    idx = tt_docs.load_index(sym)
    n, year_ago = 0, today - dt.timedelta(days=365)
    recent = [d for d in tt_docs.items(docs) if (tt_docs.f_date(d) or dt.date.min) >= year_ago]
    for typ in ('concall', 'presentation'):
        latest = next((d for d in recent if d.get('doc_type') == typ and (d.get('links') or {}).get('markdown_url')), None)
        if latest:
            n += tt_docs.get_parsed_doc(sym, idx, latest)
    if not n:
        ar = next((d for d in tt_docs.items(docs) if d.get('doc_type') == 'annual_report' and (d.get('links') or {}).get('markdown_url')), None)
        if ar:
            n += tt_docs.get_parsed_doc(sym, idx, ar)
    tt_docs.save_index(sym, idx)
    return n

try:
    for s in syms:
        print(s, 'documents downloaded:', gate_fetch(s))
except tt.QuotaExceeded as e:
    print('QUOTA EXCEEDED at', s, '- re-run after the reset; cached companies are skipped.', e)
    sys.exit(3)
finally:
    calls1 = sum(1 for _ in open(tt.CALL_LOG, encoding='utf-8')) if os.path.exists(tt.CALL_LOG) else 0
    print('Tapetide calls used:', calls1 - calls0 - (1 if calls0 == 0 and calls1 else 0))
