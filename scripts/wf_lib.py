# Shared helpers for the workflow scripts (run.py, screens.py, sectors.py, thesis.py, sheet_write.py); not run by itself.
# Atomic writes (temp file, then rename), the screener cache (data/companies/<SYM>/scr/<name>.json), industry labels,
# quarter names (FYyyQn: Indian fiscal year, Q1 = Apr-Jun ... Q4 = Jan-Mar, FY27 ends Mar 2027), and the sheet through
# the gws CLI (kite_holdings.py's gws(), sheet_get() and SHEET; its GWS_EXE override serves tests too).
# Standard library only, so every script that imports it can run with python -I.
import csv, datetime as dt, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COMPANIES_DIR, run_dir  # noqa: E402,F401
from mb_features import add_years, fnum, load, month_end, parse_period, series  # noqa: E402,F401

RUN_RE = re.compile(r'^FY(\d{2})Q([1-4])(_full)?$')
QRE = re.compile(r'^FY(\d{2})Q([1-4])$')
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def fail(msg, code=1):
    """Print a clear error line and exit non-zero."""
    print(f'ERROR: {msg}', file=sys.stderr, flush=True)
    sys.exit(code)


# ---------- quarters ----------
def fyq_end(fyq):
    """'FY27Q2' -> date(2026, 9, 30)."""
    m = QRE.match(fyq or '')
    if not m:
        raise ValueError(f'not a quarter name: {fyq!r} (FYyyQn, n = 1-4)')
    fy, q = 2000 + int(m.group(1)), int(m.group(2))
    y, mo = (fy - 1, 3 * q + 3) if q < 4 else (fy, 3)
    return month_end(y, mo)


def fyq_of(d):
    """date (any day of a quarter) -> 'FYyyQn'."""
    q = {4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3, 1: 4, 2: 4, 3: 4}[d.month]
    fy = d.year + 1 if d.month >= 4 else d.year
    return f'FY{fy % 100:02d}Q{q}'


def fyq_of_label(label):
    """screener period label 'Sep 2026' (or '30-SEP-2026') -> 'FY27Q2'."""
    return fyq_of(parse_period(label)[0])


def fyq_index(fyq):
    """A running quarter number, so differences count quarters."""
    m = QRE.match(fyq or '')
    if not m:
        raise ValueError(f'not a quarter name: {fyq!r}')
    return int(m.group(1)) * 4 + int(m.group(2))


# ---------- files ----------
def _atomic(path, write):
    d = os.path.dirname(path) or '.'
    os.makedirs(d, exist_ok=True)
    tmp = f'{path}.tmp{os.getpid()}'
    with open(tmp, 'w', encoding='utf-8', newline='') as fh:
        write(fh)
    os.replace(tmp, path)


def write_text(path, text):
    _atomic(path, lambda fh: fh.write(text))


def write_json(path, obj):
    _atomic(path, lambda fh: json.dump(obj, fh, ensure_ascii=False, indent=1))


def write_csv(path, fields, rows, delimiter=','):
    def w(fh):
        cw = csv.DictWriter(fh, fieldnames=fields, delimiter=delimiter, extrasaction='ignore', lineterminator='\n')
        cw.writeheader()
        for r in rows:
            cw.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in fields})
    _atomic(path, w)


def append_csv(path, fields, rows):
    """Append whole rows (header first if the file is new); one write call, so a crash never leaves half a row."""
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    buf = io.StringIO()
    cw = csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
    if new:
        cw.writeheader()
    for r in rows:
        cw.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in fields})
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'a', encoding='utf-8', newline='') as fh:
        fh.write(buf.getvalue())


def read_csv(path, delimiter=','):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def read_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


# ---------- the screener cache ----------
def scr_path(sym, name):
    return os.path.join(COMPANIES_DIR, sym, 'scr', name + '.json')


def scr(sym, name):
    """The `data` of a cached screener answer, or None."""
    return load(scr_path(sym, name))


_labels = {}


def industry(sym):
    """The industry label (the last, narrowest element of overview.json `sectors`, as mb_sector_test.py), or None."""
    if sym not in _labels:
        s = [x for x in ((scr(sym, 'overview') or {}).get('sectors') or []) if x]
        _labels[sym] = s[-1] if s else None
    return _labels[sym]


def table(data):
    """A screener table {label: [values]} plus its period labels (quarters or years)."""
    if not data:
        return {}, []
    periods = data.get('quarters') or data.get('years') or []
    rows = {}
    for r in data.get('rows') or []:
        rows.setdefault(r.get('label'), [fnum(v) for v in (r.get('values') or [])])
    return rows, periods


def holdings_syms(path):
    return [r['sym'] for r in read_csv(path)] if os.path.exists(path) else []


# ---------- the sheet (gws) ----------
def gws_mod():
    import kite_holdings  # reused: gws(), sheet_get(), SheetError, SHEET
    return kite_holdings


def sheet_meta():
    """{title: sheetId} of every tab."""
    k = gws_mod()
    d = k.gws('sheets', 'spreadsheets', 'get', '--params',
              json.dumps({'spreadsheetId': k.SHEET, 'fields': 'sheets.properties(sheetId,title)'}))
    return {s['properties']['title']: s['properties']['sheetId'] for s in d.get('sheets', [])}


def sheet_get(ranges, render='UNFORMATTED_VALUE'):
    return gws_mod().sheet_get(ranges, render)


def sheet_put(data):
    """data: [(range with tab, [[...]])], RAW so tickers, codes and dates stay as sent."""
    k = gws_mod()
    body = {'valueInputOption': 'RAW', 'data': [{'range': a, 'values': v} for a, v in data]}
    return k.gws('sheets', 'spreadsheets', 'values', 'batchUpdate', '--params', json.dumps({'spreadsheetId': k.SHEET}), body=body)


def sheet_clear(ranges):
    k = gws_mod()
    return k.gws('sheets', 'spreadsheets', 'values', 'batchClear', '--params', json.dumps({'spreadsheetId': k.SHEET}),
                 body={'ranges': ranges})


def sheet_batch(requests):
    k = gws_mod()
    return k.gws('sheets', 'spreadsheets', 'batchUpdate', '--params', json.dumps({'spreadsheetId': k.SHEET}),
                 body={'requests': requests})


def quote_tab(title):
    return "'" + title.replace("'", "''") + "'" if re.search(r'[^A-Za-z0-9_]', title) else title


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch.upper()) - 64
    return n - 1


def col_letters(i):
    s, i = '', i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s
