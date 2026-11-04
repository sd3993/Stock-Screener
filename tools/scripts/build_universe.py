import csv, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import run_dir
# F2: builds <run>/universe.csv from every saved screener page in <run>/screens/ (<ID>_p<NN>.json, saved by scr_tool.py, or scr_save.py before 3 Nov 2026):
# screen pages T*, whole-market band pages B* (<ID>_<desc|asc>_p<NN>.json). One row per symbol: hits (screens that matched), in_sweep, and every field
# found, under screener's field names. Checks that each band's rows add up to its total and that every column in
# process/future/screens.json came back.
base = run_dir()
cfg = json.load(open('process/future/screens.json', encoding='utf-8'))
rows, hits, swept, totals, warn = {}, {}, set(), {}, []
for fn in sorted(glob.glob(os.path.join(base, 'screens', '*_p*.json'))):
    sid = re.sub(r'_(asc|desc)$', '', re.match(r'(.+)_p\d+\.json$', os.path.basename(fn)).group(1))
    data = json.load(open(fn, encoding='utf-8'))['data']
    t = totals.setdefault(sid, [data.get('total_matches'), set()])
    for r in data.get('results', []):
        t[1].add(r['symbol'])  # asc and desc pages overlap: count distinct companies
        row = rows.setdefault(r['symbol'], {'sym': r['symbol'], 'name': r.get('name') or '', 'screener_id': r.get('company_id')})
        row.update({k: v for k, v in (r.get('fundamentals') or {}).items() if v is not None})
        if sid.startswith('B'):
            swept.add(r['symbol'])
        elif sid.startswith('T'):
            hits.setdefault(r['symbol'], set()).add(sid)  # Q* pages (extra sweeps) only add fields
for sid, (total, got) in sorted(totals.items()):
    if total is not None and len(got) != total:
        warn.append(f'{sid}: {len(got)} companies saved of {total}: a page is missing')
missing_cols = [c for c in cfg['columns'] + cfg.get('query_fields', []) if not any(c in r for r in rows.values())]
if missing_cols:
    warn.append(f'columns never returned (check the account column set): {missing_cols}')
keys = ['sym', 'name', 'screener_id', 'hits', 'in_sweep']
for r in rows.values():
    keys += [k for k in r if k not in keys]
order = lambda s: sorted(s, key=lambda x: (len(x), x))
with open(os.path.join(base, 'universe.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    for s, r in sorted(rows.items()):
        r['hits'] = '+'.join(order(hits.get(s, ())))
        r['in_sweep'] = s in swept
        w.writerow(r)
for x in warn:
    print('WARNING', x)
print('companies', len(rows), 'screen hits', len(hits), 'in sweep', len(swept))
