import csv, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import run_dir
# P2: builds <run>/universe.csv from every saved screen and dump page in <run>/screens/ (REST or MCP pages).
# One row per symbol: hits (screens that matched), in_dump, and every field found, under the screener's full
# ratio names. MCP pages name their columns with short keys: the default ones are mapped below; a dump's two
# extra columns are mapped to its 'fields' in process/screens.json, in order.
base = run_dir()
cfg = json.load(open('process/screens.json', encoding='utf-8'))
MCP_DEFAULT = {'cmp_rs.': 'Current Price', 'p/e': 'Price to Earning', 'mar_cap_rs.cr.': 'Market Capitalization',
               'div_yld_%': 'Dividend yield', 'np_qtr_rs.cr.': 'Net profit latest quarter',
               'qtr_profit_var_%': 'YOY Quarterly profit growth', 'sales_qtr_rs.cr.': 'Sales latest quarter',
               'qtr_sales_var_%': 'YOY Quarterly sales growth', 'roce_%': 'Return on capital employed'}
REST_DEFAULT = {'ltp': 'Current Price', 'pe': 'Price to Earning', 'market_cap_cr': 'Market Capitalization',
                'dividend_yield_pct': 'Dividend yield', 'net_profit_qtr_cr': 'Net profit latest quarter',
                'profit_growth_qtr_pct': 'YOY Quarterly profit growth', 'sales_qtr_cr': 'Sales latest quarter',
                'sales_growth_qtr_pct': 'YOY Quarterly sales growth', 'roce_pct': 'Return on capital employed',
                'roe_pct': 'Return on equity'}
rows, hits, dumped, warn = {}, {}, set(), []
for fn in sorted(glob.glob(os.path.join(base, 'screens', '*_p*.json'))):
    sid = re.match(r'(.+)_p\d+\.json$', os.path.basename(fn)).group(1)
    body = json.load(open(fn, encoding='utf-8'))
    is_dump = sid.startswith('D')
    if isinstance(body.get('data'), list):  # REST page
        for r in body['data']:
            row = rows.setdefault(r['symbol'], {'sym': r['symbol'], 'name': r.get('name') or ''})
            row.update({v: r.get(k) for k, v in REST_DEFAULT.items() if r.get(k) is not None})
            row.update({k: v for k, v in (r.get('ratio_values') or {}).items() if v is not None})
            (dumped.add(r['symbol']) if is_dump else hits.setdefault(r['symbol'], set()).add(sid))
    else:  # MCP page
        d = body.get('data', body)
        extras = [c for c in d.get('columns', []) if c not in MCP_DEFAULT]
        fields = cfg['dumps'].get(sid, {}).get('fields') if is_dump else None
        if fields and len(extras) != len(fields):
            warn.append(f'{fn}: extra columns {extras} vs fields {fields}')
        for r in d.get('results', []):
            row = rows.setdefault(r['symbol'], {'sym': r['symbol'], 'name': r.get('name') or ''})
            cols = r.get('columns') or {}
            for k, v in cols.items():
                if v is None:
                    continue
                if k in MCP_DEFAULT:
                    row[MCP_DEFAULT[k]] = v
                elif fields and len(extras) == len(fields):
                    row[fields[extras.index(k)]] = v
                else:
                    row['x:' + k] = v
            (dumped.add(r['symbol']) if is_dump else hits.setdefault(r['symbol'], set()).add(sid))
keys = ['sym', 'name', 'hits', 'in_dump']
for r in rows.values():
    keys += [k for k in r if k not in keys]
order = lambda s: sorted(s, key=lambda x: (len(x), x))
with open(os.path.join(base, 'universe.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    for s, r in sorted(rows.items()):
        r['hits'] = '+'.join(order(hits.get(s, ())))
        r['in_dump'] = s in dumped
        w.writerow(r)
for x in warn:
    print('WARNING', x)
print('companies', len(rows), 'screen hits', len(hits), 'in dumps', len(dumped))
