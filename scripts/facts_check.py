"""S10 check: compares a company's facts.json (figures read from its filings) with the cached screener.in answers in
data/companies/<SYM>/scr/ (basis as requested in the call). Writes facts_check.json beside facts.json. Read-only on everything else.
usage: python scripts/facts_check.py SYM
"""
import json, os, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COMPANIES_DIR as FILINGS_DIR
sym = sys.argv[1]
d = os.path.join(FILINGS_DIR, sym)
fp = os.path.join(d, 'facts.json')
if not os.path.exists(fp):
    sys.exit(f'no facts.json in {d}')
facts = json.load(open(fp, encoding='utf-8-sig'))

def load(path):
    return json.load(open(path, encoding='utf-8-sig')) if os.path.exists(path) else None

# Every source in one layout: {section: {row label lower: {period: value}}}, plus the basis it is on.
def from_screener():
    out, bases = {}, set()
    for sec in ('quarterly', 'profit_loss', 'balance_sheet', 'cash_flow', 'shareholding'):
        env = load(os.path.join(d, 'scr', sec + '.json'))
        if not env:
            continue
        data = env['data']
        periods = data.get('quarters') or data.get('years') or []
        out[sec] = {r['label'].strip().lower(): dict(zip(periods, r['values'])) for r in data.get('rows', [])}
        if sec != 'shareholding':
            bases.add(env['args'].get('financial_type') or data.get('financial_type') or 'consolidated')
    return out, bases

SOURCES = {name: f() for name, f in (('screener', from_screener),)}
SOURCES = {k: v for k, v in SOURCES.items() if v[0]}
QMAP = {'revenue': ('quarterly', 'sales'), 'pat': ('quarterly', 'net profit'), 'pbt': ('quarterly', 'profit before tax'),
        'eps': ('quarterly', 'eps in rs')}
AMAP = {'revenue': ('profit_loss', 'sales'), 'pat': ('profit_loss', 'net profit'), 'pbt': ('profit_loss', 'profit before tax'),
        'eps': ('profit_loss', 'eps in rs'), 'cfo': ('cash_flow', 'cash from operating activity'),
        'borrowings': ('balance_sheet', 'borrowings')}
val = lambda x: x.get('value') if isinstance(x, dict) else x
rows, missing = [], []

def cmp(kind, period, field, fv, sec, lab, note=''):
    for src, (S, _) in SOURCES.items():
        tv = (S.get(sec, {}).get(lab) or {}).get(period)
        if fv is None or tv is None:
            missing.append(f'{kind} {period} {field} [{src}]: facts={fv} source={tv}')
            continue
        diff = abs(fv - tv) / max(abs(fv), abs(tv), 1e-9) * 100
        # screener rounds to whole crore: a gap under 0.5 cr is rounding
        rows.append({'kind': kind, 'period': period, 'field': field, 'source': src, 'facts': fv, 'value': tv,
                     'diff_pct': round(diff, 2), 'flag': diff > 2 and abs(fv - tv) > 0.5, 'note': note})

for kind, table, M in (('quarter', facts.get('quarterly') or {}, QMAP), ('annual', facts.get('annual') or {}, AMAP)):
    for period, f in table.items():
        for k, (sec, lab) in M.items():
            if k in f:
                cmp(kind, period, k, val(f[k]), sec, lab, 'source borrowings may include leases' if k == 'borrowings' else '')
for period, f in (facts.get('shareholding') or {}).items():
    if isinstance(f, dict) and 'promoter_pct' in f:
        cmp('shareholding', period, 'promoter_pct', val(f['promoter_pct']), 'shareholding', 'promoters')

out = {'sym': sym, 'sources': {k: {'basis': sorted(b for b in v[1] if b), 'sections': sorted(v[0])} for k, v in SOURCES.items()},
       'checked': len(rows), 'flags': [r for r in rows if r['flag']], 'all': rows, 'not_compared': missing}
json.dump(out, open(os.path.join(d, 'facts_check.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{sym}: {len(rows)} compared ({', '.join(SOURCES) or 'no source cached'}), {len(out['flags'])} flagged, {len(missing)} not compared")
for r in out['flags']:
    print(f"  {r['kind']} {r['period']} {r['field']} [{r['source']}]: facts {r['facts']} vs {r['value']} ({r['diff_pct']}%) {r['note']}")
