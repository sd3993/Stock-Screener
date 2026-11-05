import csv, glob, json, os, sys
# Multibagger study, P1 (process/past/p1_universe.md): builds runs/past/<date>/universe.csv from the
# saved screener band pages (runs/past/<date>/universe/U<band>_<asc|desc>_p<n>.json, saved with scr_save.py) plus the
# delisted candidates in data/market/reference_stocks_delisted.json. Columns: sym, screener_id, name, mc_now, status.
# Prints each band's distinct companies against screener's total_matches, so a missing page shows.
#   python -I tools/scripts/mb_universe.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir
D = hist_dir()
rows, bands = {}, {}
for f in sorted(glob.glob(os.path.join(D, 'universe', 'U*.json'))):
    d = json.load(open(f, encoding='utf-8'))['data']
    band = os.path.basename(f).split('_')[0]
    b = bands.setdefault(band, {'total': d.get('total_matches'), 'syms': set()})
    for r in d.get('results', []):
        b['syms'].add(r['symbol'])
        rows[r['symbol']] = {'sym': r['symbol'], 'screener_id': r.get('company_id', ''), 'name': r.get('name', ''),
                             'mc_now': (r.get('fundamentals') or {}).get('Market Capitalization', ''), 'status': 'listed'}
short = [k for k, b in bands.items() if b['total'] is not None and len(b['syms']) < b['total']]
for k, b in sorted(bands.items()):
    print(k, len(b['syms']), 'of', b['total'])
dl = os.path.join('data', 'market', 'reference_stocks_delisted.json')
n_dl = 0
if os.path.exists(dl):
    for r in json.load(open(dl, encoding='utf-8'))['data']['data']:
        if r['symbol'] not in rows:
            rows[r['symbol']] = {'sym': r['symbol'], 'screener_id': '', 'name': r.get('name', ''), 'mc_now': '', 'status': 'delisted'}
            n_dl += 1
out = sorted(rows.values(), key=lambda r: (r['status'] != 'listed', float(r['mc_now'] or 0)))
with open(os.path.join(D, 'universe.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['sym', 'screener_id', 'name', 'mc_now', 'status'])
    w.writeheader(); w.writerows(out)
print('universe.csv:', len(out) - n_dl, 'listed,', n_dl, 'delisted', '| SHORT BANDS: ' + ', '.join(short) if short else '')
