# Pulls holdings through the official Kite CLI (read-only) and writes the same data to two copies:
#   - data/kite/: holdings_<YYYY-MM-DD_HHMM>.json (the CLI's answer as is) and holdings.csv (the latest, one row per stock);
#   - the sheet's Holdings tab (sheetId 104) through the gws CLI: only the data columns (layout: tools/tools.md, "Holdings tab").
#     Status (F) and the Notes cells (M2 down) are F10's decisions and are never written; only the header M1 gets the fetch time.
#     Rows are never deleted (sold => Qty 0).
# Kite unavailable: changes nothing except the sheet's Kite-stale column (Q = TRUE on every holding row), prints when each
#   copy was last fetched and which is newer, exits 3.
# gws unavailable or a sheet write fails: the local copy is still saved; prints a line starting "SHEET NOT UPDATED", exits 0.
# Usage (from the project root):
#   python tools/scripts/kite_holdings.py                 fetch from Kite, write local and sheet
#   python tools/scripts/kite_holdings.py --latest PATH   no Kite: write the newer of local holdings.csv / sheet to PATH
# Overrides (tests): env KITE_EXE, GWS_EXE.
import argparse, csv, datetime as dt, json, os, re, subprocess, sys, time

KITE = os.environ.get('KITE_EXE') or os.path.expandvars(r'%LOCALAPPDATA%\Programs\kite\kite.exe')
GWS = os.environ.get('GWS_EXE') or os.path.expandvars(r'%LOCALAPPDATA%\Programs\gws\gws.exe')
SHEET = '1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU'
TAB = 'Holdings'
FIRST, LAST = 2, 100            # rows with pre-filled formulas
HDR, HDR_TEXT = 'M1', 'Notes · Kite fetched '      # Notes header cell carries the fetch time: "Notes · Kite fetched YYYY-MM-DD HH:MM"
OLD_STAMP = 'T1:U1'     # old home of the stamp (label, value); read as a fallback for one transition, then cleared
STAMP_RE = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
OUT = os.path.join('data', 'kite')
LATEST = os.path.join(OUT, 'holdings.csv')
FIELDS = ['sym', 'exchange', 'isin', 'name', 'qty', 'avg_cost', 'last_price', 'google_code', 'screener_url', 'fetched_at']
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


class SheetError(Exception):
    pass


def gws(*args, body=None):
    cmd = [GWS, *args]
    if body is not None:
        cmd += ['--json', json.dumps(body)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    except OSError as e:
        raise SheetError(f'gws not found at {GWS}: {e}')
    if r.returncode != 0:
        raise SheetError(f'gws exit {r.returncode}: {(r.stdout or r.stderr).strip()[:300]}')
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise SheetError(f'gws gave no JSON: {r.stdout.strip()[:200]}')


def sheet_get(ranges, render='UNFORMATTED_VALUE'):
    p = {'spreadsheetId': SHEET, 'ranges': ranges, 'valueRenderOption': render}
    d = gws('sheets', 'spreadsheets', 'values', 'batchGet', '--params', json.dumps(p))
    return [vr.get('values', []) for vr in d.get('valueRanges', [])]


def sheet_put(data):  # data: [(range, [[...]])], RAW so tickers, codes and dates stay as sent
    p = {'spreadsheetId': SHEET}
    body = {'valueInputOption': 'RAW', 'data': [{'range': f'{TAB}!{a}', 'values': v} for a, v in data]}
    gws('sheets', 'spreadsheets', 'values', 'batchUpdate', '--params', json.dumps(p), body=body)


def col(vals, i):  # column i of a 2-D answer, padded to rows FIRST..LAST
    out = [(r[i] if i < len(r) else '') for r in vals]
    return out + [''] * (LAST - FIRST + 1 - len(out))


def read_tab():
    """Sheet holdings rows {row: {...}} and the Kite-fetched stamp."""
    v, hdr, old = sheet_get([f'{TAB}!A{FIRST}:Z{LAST}', f'{TAB}!{HDR}', f'{TAB}!{OLD_STAMP}'])
    idx = {k: ord(k) - 65 for k in 'BCDNOPQVZ'}
    cols = {k: col(v, i) for k, i in idx.items()}
    rows = {}
    for n in range(LAST - FIRST + 1):
        rows[FIRST + n] = {k: cols[k][n] for k in idx}
    m = STAMP_RE.search(str(hdr[0][0])) if hdr and hdr[0] else None
    if m:
        return rows, m.group(0)
    o = old[0][1] if old and len(old[0]) > 1 else ''   # transition: the old U1 stamp
    return rows, (str(o) if STAMP_RE.fullmatch(str(o)) else '')


def last_local():
    try:
        with open(LATEST, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        return rows, (rows[0]['fetched_at'] if rows else '')
    except FileNotFoundError:
        return [], ''


def kite(*args):
    try:
        r = subprocess.run([KITE, '--json', *args], capture_output=True, text=True, encoding='utf-8')
    except OSError as e:
        return None, {'type': 'CLI missing', 'message': f'kite CLI not found at {KITE}: {e}'}
    try:
        data = json.loads(r.stdout)
    except ValueError:
        data = None
    if r.returncode != 0 or data is None or (isinstance(data, dict) and data.get('ok') is False):
        err = data.get('error', {}) if isinstance(data, dict) else {'message': (r.stdout or r.stderr).strip()[:200]}
        return None, err
    return data, None


def compare(local_stamp, sheet_stamp, sheet_err):
    s = f'local data/kite/holdings.csv fetched {local_stamp or "never"}; '
    if sheet_err:
        return s + f'sheet not readable ({sheet_err})', 'local'
    s += f'sheet Holdings tab fetched {sheet_stamp or "never (no Kite fetched stamp)"}; '
    newer = 'sheet' if sheet_stamp and sheet_stamp > local_stamp else 'local'
    if local_stamp and local_stamp == sheet_stamp:
        return s + 'both the same fetch', 'local'
    return s + f'newer: {newer}', newer


# ---------- --latest: the newer copy, without Kite ----------
def latest(path):
    lrows, lstamp = last_local()
    try:
        srows, sstamp = read_tab()
        err = None
    except SheetError as e:
        srows, sstamp, err = {}, '', str(e)
    msg, newer = compare(lstamp, sstamp, err)
    print(msg)
    if newer == 'local':
        out = lrows
    else:
        out = []
        for r in srows.values():
            if not r['Z'] or r['C'] in ('', 0):
                continue  # empty or sold row
            code = str(r['N'])
            out.append({'sym': r['Z'], 'exchange': 'BSE' if code.startswith('BOM:') else 'NSE', 'isin': r['V'],
                        'name': r['B'], 'qty': r['C'], 'avg_cost': r['D'], 'last_price': r['P'],
                        'google_code': code, 'screener_url': r['O'], 'fetched_at': sstamp})
    if not out:
        print('no holdings in the newer copy; nothing written')
        return 1
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(out)
    print(f'{len(out)} holdings from the {newer} copy written to {path}')
    return 0


# ---------- names and codes ----------
def data_tab():
    """Data tab's ticker -> (google code, screener url, name), as F9 wrote them."""
    v, = sheet_get(['Data!A2:D300'])
    return {r[0]: (r[1] if len(r) > 1 else '', r[2] if len(r) > 2 else '', r[3] if len(r) > 3 else '')
            for r in v if r and r[0]}


def cached_name(sym):
    try:
        with open(os.path.join('data', 'companies', sym, 'scr', 'overview.json'), encoding='utf-8') as f:
            return (json.load(f).get('data') or {}).get('name') or ''
    except (OSError, ValueError):
        return ''


def identity(h, known):
    """(name, google code, screener url) for one Kite holding."""
    sym = h['tradingsymbol']
    g, u, n = known.get(sym, ('', '', ''))
    if g and u and n:
        return n, g, u
    nse, kname = h.get('exchange') == 'NSE', ''
    ans, _ = kite('market', 'resolve', f'NSE:{sym}', '--exchange', 'NSE', '--limit', '0')
    time.sleep(0.15)  # Kite REST limit 10/s
    for m in (ans or {}).get('matches', []):
        if m.get('tradingsymbol') == sym and m.get('exchange') == 'NSE':
            nse, kname = True, m.get('name') or ''
    if nse:
        g, u = g or f'NSE:{sym}', u or f'https://www.screener.in/company/{sym}/consolidated/'
    else:  # BSE-only: a BSE instrument_token is the BSE scrip code shifted left 8 bits
        code = int(h['instrument_token']) >> 8
        if not (n or cached_name(sym)):
            ans, _ = kite('market', 'resolve', f'BSE:{sym}', '--exchange', 'BSE', '--limit', '0')
            time.sleep(0.15)
            kname = next((m.get('name') or '' for m in (ans or {}).get('matches', []) if m.get('tradingsymbol') == sym), '')
        g, u = g or f'BOM:{code}', u or f'https://www.screener.in/company/{code}/consolidated/'
    return n or cached_name(sym) or kname.title(), g, u


# ---------- sheet sync ----------
def fill_identity(rows, data):
    """Name, Google code and screener URL for each row (Data tab first, else Kite and the screener cache)."""
    by_sym = {h['tradingsymbol']: h for h in data}
    try:
        known = data_tab()
    except SheetError:
        known = {}
    for row in rows:
        name, g, u = identity(by_sym[row['sym']], known)
        row.update(name=name, google_code=g, screener_url=u)


def sync_sheet(rows, stamp):
    try:
        sheet, _ = read_tab()
    except SheetError as e:
        return f'SHEET NOT UPDATED (could not read it: {e}); local copy saved'
    free = [r for r, s in sheet.items() if not s['Z']]
    used, writes, notes = set(), [], []
    for row in rows:
        r = next((n for n, s in sheet.items() if n not in used and s['V'] and s['V'] == row['isin']), None)
        if r is None:
            r = next((n for n, s in sheet.items() if n not in used and s['Z'] == row['sym']
                      and (not s['V'] or not row['isin'])), None)
        if r is None:
            if not free:
                notes.append(f'NO FREE ROW for {row["sym"]} (rows {FIRST}-{LAST} full); not written')
                continue
            r = free.pop(0)
            notes.append(f'new holding {row["sym"]} added at row {r} (status/notes for F10)')
        elif sheet[r]['Z'] != row['sym']:
            notes.append(f'row {r}: ticker {sheet[r]["Z"]} -> {row["sym"]} (same ISIN {row["isin"]})')
        used.add(r)
        name, g, u = row['name'], row['google_code'], row['screener_url']
        writes += [(f'B{r}:D{r}', [[name, row['qty'], row['avg_cost']]]),
                   (f'N{r}:Q{r}', [[g, u, row['last_price'], False]]),
                   (f'V{r}', [[row['isin'] or sheet[r]['V']]]), (f'Z{r}', [[row['sym']]])]
    for n, s in sheet.items():
        if s['Z'] and n not in used:
            if s['C'] not in (0, '0'):
                notes.append(f'sold: {s["Z"]} (row {n}) Qty set to 0; F10 removes the row')
            writes += [(f'C{n}', [[0]]), (f'Q{n}', [[False]])]
    writes += [(HDR, [[HDR_TEXT + stamp]])]
    try:
        old, = sheet_get([f'{TAB}!{OLD_STAMP}'])
        if any(c != '' for r in old for c in r):   # clear the old stamp cells once
            writes += [(OLD_STAMP, [['', '']])]
        sheet_put(writes)
        after, astamp = read_tab()
    except SheetError as e:
        return '\n'.join(notes + [f'SHEET NOT UPDATED (write failed: {e}); local copy saved'])
    bad = []
    for row in rows:
        r = next((n for n, s in after.items() if s['Z'] == row['sym']), None)
        if r is None or float(after[r]['C']) != float(row['qty']) or abs(float(after[r]['D']) - float(row['avg_cost'])) > 1e-6:
            bad.append(row['sym'])
    if astamp != stamp:
        bad.append(f'stamp {astamp!r}')
    status = f'SHEET CHECK FAILED for {bad}' if bad else f'sheet Holdings tab updated and read back ({len(rows)} holdings, Kite fetched {stamp} in {HDR})'
    return '\n'.join(notes + [status])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--latest', metavar='PATH', help='no Kite: write the newer of local holdings.csv / sheet to PATH')
    a = ap.parse_args()
    if a.latest:
        return latest(a.latest)

    data, err = kite('portfolio', 'holdings')
    if err or not isinstance(data, list):
        err = err or {'message': 'unexpected answer'}
        print(f'Kite not available ({err.get("type", "error")}: {err.get("message")}); nothing fetched')
        _, lstamp = last_local()
        try:
            sheet, sstamp = read_tab()
            stale = [(f'Q{n}', [[True]]) for n, s in sheet.items() if s['Z']]
            if stale:
                sheet_put(stale)
            print(compare(lstamp, sstamp, None)[0])
            print(f'sheet: Kite stale (Q) set TRUE on {len(stale)} holding rows; nothing else written')
        except SheetError as e:
            print(compare(lstamp, '', str(e))[0])
            print('SHEET NOT UPDATED (Kite stale not set)')
        return 3

    now = dt.datetime.now(IST)
    stamp = now.strftime('%Y-%m-%d %H:%M')
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'holdings_{now:%Y-%m-%d_%H%M}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    rows, odd = [], []
    for h in data:
        parts = {'t1': h.get('t1_quantity') or 0, 'collateral': h.get('collateral_quantity') or 0,
                 'mtf': (h.get('mtf') or {}).get('quantity') or 0}
        if any(parts.values()):  # never seen yet: check against Kite web once, then record the rule in tools.md
            odd.append(f'{h["tradingsymbol"]} {parts}')
        rows.append({'sym': h['tradingsymbol'], 'exchange': h.get('exchange'), 'isin': h.get('isin'), 'name': '',
                     'qty': h['quantity'] + sum(parts.values()), 'avg_cost': h.get('average_price'),
                     'last_price': h.get('last_price'), 'google_code': '', 'screener_url': '', 'fetched_at': stamp})
    fill_identity(rows, data)
    sheet_msg = sync_sheet(rows, stamp)
    with open(LATEST, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} holdings saved to {LATEST} (Kite fetched {stamp})')
    print(sheet_msg)
    if odd:
        print('CHECK: T+1/collateral/MTF quantities added to qty; confirm against Kite web: ' + '; '.join(odd))
    return 0


if __name__ == '__main__':
    sys.exit(main())
