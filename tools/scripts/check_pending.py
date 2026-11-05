import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import run_dir
# Pending check: lists companies in <run>/company_list.csv that haven't finished F10 (sheet listing), from <run>/status.csv.
# usage: python tools/scripts/check_pending.py [runs/<FYyyQn>]
run = sys.argv[1] if len(sys.argv) > 1 else run_dir()
companies = [r['sym'] for r in csv.DictReader(open(os.path.join(run, 'company_list.csv'), encoding='utf-8-sig'))]
sp = os.path.join(run, 'status.csv')
status = {r['sym']: r for r in csv.DictReader(open(sp, encoding='utf-8-sig'))} if os.path.exists(sp) else {}
pending = []
for s in companies:
    r = status.get(s)
    if not r or not (r['phase'] == 'F10' and r['state'] == 'done'):
        pending.append((s, r['phase'] if r else '-', r['state'] if r else 'not started', r.get('stage', '') if r else ''))
for s, phase, state, stage in pending:
    print(f'{s}\t{phase}\t{state}\t{stage}')
print(f'PENDING: {len(pending)}')
