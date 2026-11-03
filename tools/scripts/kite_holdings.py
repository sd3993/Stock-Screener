# Pulls holdings through the official Kite CLI (read-only) and keeps them outside the runs, in data/kite/:
# holdings_<YYYY-MM-DD_HHMM>.json (the CLI's answer as is) and holdings.csv (the latest, one row per stock).
# When Kite isn't logged in it changes nothing, prints when the last saved holdings were fetched and exits 3,
# so a run carries on with data/kite/holdings.csv (or the sheet's Holdings tab).
# Usage: python tools/scripts/kite_holdings.py
import csv, datetime as dt, json, os, subprocess, sys

KITE = os.path.expandvars(r'%LOCALAPPDATA%\Programs\kite\kite.exe')
OUT = os.path.join('data', 'kite')
LATEST = os.path.join(OUT, 'holdings.csv')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

def last_saved():
    try:
        with open(LATEST, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        return f'{len(rows)} holdings fetched {rows[0]["fetched_at"]}' if rows else 'empty file'
    except FileNotFoundError:
        return 'none saved yet'

try:
    r = subprocess.run([KITE, '--json', 'portfolio', 'holdings'], capture_output=True, text=True, encoding='utf-8')
except OSError as e:  # CLI missing: same fallback as a missing login
    r = subprocess.CompletedProcess([], 1, '', f'kite CLI not found at {KITE}: {e}')
try:
    data = json.loads(r.stdout)
except ValueError:
    data = None
if r.returncode != 0 or not isinstance(data, list):
    err = data.get('error', {}) if isinstance(data, dict) else {'message': (r.stdout or r.stderr).strip()[:200]}
    print(f'Kite not available ({err.get("type", "error")}: {err.get("message")}); last saved: {last_saved()}')
    sys.exit(3)

now = dt.datetime.now(IST)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, f'holdings_{now:%Y-%m-%d_%H%M}.json'), 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

rows, odd = [], []
for h in data:
    parts = {'t1': h.get('t1_quantity') or 0, 'collateral': h.get('collateral_quantity') or 0,
             'mtf': (h.get('mtf') or {}).get('quantity') or 0}
    if any(parts.values()):  # never seen yet: check against Kite web once, then record the rule in tools.md
        odd.append(f'{h["tradingsymbol"]} {parts}')
    rows.append({'sym': h['tradingsymbol'], 'exchange': h.get('exchange'), 'isin': h.get('isin'),
                 'qty': h['quantity'] + sum(parts.values()), 'avg_cost': h.get('average_price'),
                 'last_price': h.get('last_price'), 'fetched_at': now.strftime('%Y-%m-%d %H:%M')})
with open(LATEST, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['sym'])
    w.writeheader()
    w.writerows(rows)
print(f'{len(rows)} holdings saved to {LATEST}')
if odd:
    print('CHECK: T+1/collateral/MTF quantities added to qty; confirm against Kite web: ' + '; '.join(odd))
