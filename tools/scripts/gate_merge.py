import csv, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import run_dir
# P4R: writes <run>/gate/decisions.csv from each batch's latest file (bNN_rc2 > bNN_rc1 > bNN).
g = os.path.join(run_dir(), 'gate')
latest = {}
for fn in glob.glob(os.path.join(g, 'b[0-9]*.json')):
    m = re.match(r'b(\d+)(?:_rc(\d+))?\.json$', os.path.basename(fn))
    if m:
        b, rc = int(m.group(1)), int(m.group(2) or 0)
        if b not in latest or rc > latest[b][0]:
            latest[b] = (rc, fn)
rows = []
for b, (rc, fn) in sorted(latest.items()):
    d = json.load(open(fn, encoding='utf-8'))
    for e in (d['entries'] if isinstance(d, dict) else d):
        rows.append({'sym': e['sym'], 'decision': e['decision'], 'batch': b, 'stage': f'rc{rc}' if rc else 'gate',
                     'est_cagr': e.get('est_cagr'), 'bucket': e.get('bucket'), 'floor_failed': e.get('floor_failed'), 'why': e.get('why')})
with open(os.path.join(g, 'decisions.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ['sym'])
    w.writeheader()
    w.writerows(rows)
unrechecked = [b for b, (rc, _) in latest.items() if rc == 0]
print('decisions', len(rows), 'NEXT', sum(r['decision'] == 'NEXT' for r in rows), 'REJECT', sum(r['decision'] == 'REJECT' for r in rows),
      '| batches not yet rechecked:', unrechecked or 'none')
