import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COMPANIES_DIR as FILINGS_DIR, api_path
# F8 check: compares a company's facts.json (figures read from its filings) with every cached data source:
# screener.in answers in data/companies/<SYM>/scr/ (basis as requested in the call) and Tapetide answers in api/
# (fundamentals, else financials). Writes facts_check.json beside facts.json. Read-only on everything else.
# usage: python tools/scripts/facts_check.py SYM
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

def from_tapetide():
    env = load(api_path(sym, 'fundamentals'))
    rows = (env or {}).get('data', {}).get('data') if env else None
    rows = [r for page in rows for r in page['data']] if rows and isinstance(rows[0], dict) and 'data' in rows[0] else rows
    out, bases = {}, set()
    lab = {'revenue': 'sales', 'net_profit': 'net profit', 'profit_before_tax': 'profit before tax', 'eps': 'eps in rs',
           'cash_from_operations': 'cash from operating activity', 'borrowings': 'borrowings'}
    for r in rows or []:
        if r.get('metric') in lab and r.get('value') is not None:
            sec = 'quarterly' if r['period_type'] == 'quarter' else {'cash_from_operations': 'cash_flow',
                                                                     'borrowings': 'balance_sheet'}.get(r['metric'], 'profit_loss')
            out.setdefault(sec, {}).setdefault(lab[r['metric']], {})[dt.date.fromisoformat(r['period_end']).strftime('%b %Y')] = r['value']
            bases.add(r.get('basis'))
    if not out:  # older caches: /financials sections (basis not stated)
        def walk(o):
            if isinstance(o, dict):
                if 'section' in o and isinstance(o.get('data'), dict):
                    out[o['section']] = {k.strip().lower(): v for k, v in o['data'].items() if isinstance(v, dict)}
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk((load(api_path(sym, 'financials')) or {}).get('data'))
        bases.add('unstated')
    sh = (load(api_path(sym, 'shareholding')) or {}).get('data')
    def find(o):
        if isinstance(o, dict):
            if isinstance(o.get('data'), dict) and 'Promoters' in o['data']:
                out.setdefault('shareholding', {})['promoters'] = o['data']['Promoters']
            for v in o.values():
                find(v)
        elif isinstance(o, list):
            for v in o:
                find(v)
    find(sh)
    return out, bases

SOURCES = {name: f() for name, f in (('screener', from_screener), ('tapetide', from_tapetide))}
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
        # screener and Tapetide round to whole crore: a gap under 0.5 cr is rounding
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
