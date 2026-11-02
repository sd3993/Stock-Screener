import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COMPANIES_DIR as FILINGS_DIR, api_path
# P6 check: compares a company's facts.json (figures read from its filings) with Tapetide's cached financials and
# shareholding, and writes facts_check.json beside facts.json. Read-only on everything else.
# usage: python tools/scripts/facts_check.py SYM
sym = sys.argv[1]
d = os.path.join(FILINGS_DIR, sym)
fp = os.path.join(d, 'facts.json')
if not os.path.exists(fp):
    sys.exit(f'no facts.json in {d}')
facts = json.load(open(fp, encoding='utf-8-sig'))

def tt_load(name):
    p = api_path(sym, name)
    return json.load(open(p, encoding='utf-8-sig'))['data'] if os.path.exists(p) else None

def sections(obj):
    """{section name: {row label lower: {period: value}}} from a financials answer, REST or MCP shape."""
    out = {}
    def walk(o):
        if isinstance(o, dict):
            if 'section' in o and isinstance(o.get('data'), dict):
                out[o['section']] = {k.strip().lower(): v for k, v in o['data'].items() if isinstance(v, dict)}
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return out

S = sections(tt_load('financials') or {})
QMAP = {'revenue': ('quarterly', 'sales'), 'pat': ('quarterly', 'net profit'), 'pbt': ('quarterly', 'profit before tax')}
AMAP = {'revenue': ('profit_loss', 'sales'), 'pat': ('profit_loss', 'net profit'), 'cfo': ('cash_flow', 'cash from operating activity'),
        'borrowings': ('balance_sheet', 'borrowings')}
val = lambda x: x.get('value') if isinstance(x, dict) else x
rows, missing = [], []

def cmp(kind, period, field, fv, tv, note=''):
    if fv is None or tv is None:
        missing.append(f'{kind} {period} {field}: facts={fv} tapetide={tv}')
        return
    base = max(abs(fv), abs(tv), 1e-9)
    diff = abs(fv - tv) / base * 100
    rows.append({'kind': kind, 'period': period, 'field': field, 'facts': fv, 'tapetide': tv, 'diff_pct': round(diff, 2),
                 'flag': diff > 2 and abs(fv - tv) > 0.5, 'note': note})

for kind, table, M in (('quarter', facts.get('quarterly') or {}, QMAP), ('annual', facts.get('annual') or {}, AMAP)):
    for period, f in table.items():
        for k, (sec, lab) in M.items():
            if k in f:
                note = 'Tapetide borrowings may include leases' if k == 'borrowings' else ''
                cmp(kind, period, k, val(f[k]), (S.get(sec, {}).get(lab) or {}).get(period), note)

sh = tt_load('shareholding')
prom = {}
if sh:
    def find(o):
        if isinstance(o, dict):
            if isinstance(o.get('data'), dict) and 'Promoters' in o['data']:
                prom.update(o['data']['Promoters'])
            for v in o.values():
                find(v)
        elif isinstance(o, list):
            for v in o:
                find(v)
    find(sh)
for period, f in ((facts.get('shareholding') or {}).items()):
    if isinstance(f, dict) and 'promoter_pct' in f:
        cmp('shareholding', period, 'promoter_pct', val(f['promoter_pct']), prom.get(period))

out = {'sym': sym, 'checked': len(rows), 'flags': [r for r in rows if r['flag']], 'all': rows, 'not_compared': missing,
       'tapetide_sections_found': sorted(S)}
json.dump(out, open(os.path.join(d, 'facts_check.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{sym}: {len(rows)} compared, {len(out['flags'])} flagged, {len(missing)} not compared")
for r in out['flags']:
    print(f"  {r['kind']} {r['period']} {r['field']}: facts {r['facts']} vs Tapetide {r['tapetide']} ({r['diff_pct']}%) {r['note']}")
