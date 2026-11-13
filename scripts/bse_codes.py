"""BSE scrip code for each NSE symbol (sources/exchanges.md), by plain curl with its default identity.
  python scripts/bse_codes.py [--syms A,B]     -> data/market/bse_codes.csv
Files (cached in data/market/ with their date): NSE's EQUITY_L.csv (SYMBOL, ISIN) and the last 5 BSE equity price files (union)
(BhavCopy_BSE_CM_0_0_0_<YYYYMMDD>_F_0000.CSV; today's is partial or missing, so it walks back to a file over 100 KB).
Columns: nse_symbol, isin, bse_code, bse_name, source:
  isin        NSE ISIN = BSE ISIN (the main join)
  scr-isin    symbol not in EQUITY_L (renamed/delisted/BSE-only): the ISIN found in data/companies/<SYM>/scr/*.json
  numeric     the company folder is named by its BSE code (BSE-only companies)
  name-match  delisted/renamed, no ISIN match: the company's name matched (unique, prefix) against an old BSE price file
              near its last trading date (scr/history.json) -- FOR REVIEW; old files cut names at ~12 characters
  unmatched   no BSE code found (NSE-only listings stay here; never a guess)
Rows: every EQUITY_L symbol, then every other folder in data/companies/. Look up with lookup(sym), used by bse_shp.py.
Result of the run on 4 Nov 2026: 2,490 ISIN matches, 30 name-matches; NSE-only and SME symbols stay unmatched.
"""
import argparse, csv, datetime as dt, glob, io, json, os, re, subprocess, sys, zipfile
MARKET = os.path.join('data', 'market')
OUT = os.path.join(MARKET, 'bse_codes.csv')
COMP = os.path.join('data', 'companies')
NEW = 'https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{d:%Y%m%d}_F_0000.CSV'
OLD = 'https://www.bseindia.com/download/BhavCopy/Equity/EQ{d:%d%m%y}_CSV.ZIP'
EQL = 'https://archives.nseindia.com/content/equities/EQUITY_L.csv'
REF = {}
COLS = ['nse_symbol', 'isin', 'bse_code', 'bse_name', 'source']


def curl(url, out, minsize=0):
    tmp = out + '.part'
    try:
        r = subprocess.run(['curl.exe', '-s', '-m', '90', '-o', tmp, '-w', '%{http_code}', url], capture_output=True,
                           text=True, timeout=110)
        ok = r.stdout.strip() == '200' and os.path.exists(tmp) and os.path.getsize(tmp) > minsize
    except subprocess.TimeoutExpired:
        ok = False
    if ok:
        os.replace(tmp, out)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return ok


def bhav(d):
    """One day's BSE price file -> list of (code, isin, name), or None. New format (ISIN) from Jul 2024, else the old zip."""
    new, old = (os.path.join(MARKET, f'bse_bhav_{d:%Y%m%d}.csv'), os.path.join(MARKET, f'bse_bhav_{d:%Y%m%d}_old.csv'))
    if not os.path.exists(new) and not os.path.exists(old):
        if not curl(NEW.format(d=d), new, 100000):
            z = os.path.join(MARKET, 'bse_tmp.zip')
            if not curl(OLD.format(d=d), z, 1000):
                return None
            try:
                with zipfile.ZipFile(z) as zf:
                    data = zf.read(zf.namelist()[0])
                open(old, 'wb').write(data)
            except zipfile.BadZipFile:
                return None
            finally:
                os.remove(z)
    if os.path.exists(new):
        return [(r['FinInstrmId'].strip(), r['ISIN'].strip(), r['FinInstrmNm'].strip())
                for r in csv.DictReader(open(new, encoding='utf-8-sig'))]
    return [(r['SC_CODE'].strip(), '', r['SC_NAME'].strip())
            for r in csv.DictReader(open(old, encoding='utf-8-sig', errors='replace'))]


def norm(s):
    s = re.sub(r'\(.*?\)', ' ', s.upper().replace('&', ' AND '))
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'\b(LIMITED|LTD|PVT|PRIVATE|THE)\b', ' ', s)
    return re.sub(r'\s+', '', s)


def load(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return None


def scr_isin(sym):
    """Most frequent ISIN (INE...) in the company's scr files, or ''."""
    cnt = {}
    for f in glob.glob(os.path.join(COMP, sym, 'scr', '*.json')):
        if os.path.basename(f) == 'history.json':
            continue
        for m in re.findall(r'IN[EF][0-9A-Z]{9}\d', open(f, encoding='utf-8', errors='replace').read()):
            cnt[m] = cnt.get(m, 0) + 1
    return max(cnt, key=cnt.get) if cnt else ''


def last_trade(sym):
    h = load(os.path.join(COMP, sym, 'scr', 'history.json'))
    try:
        return dt.date.fromisoformat(h['data']['price']['datasets']['Price'][-1][0])
    except (TypeError, KeyError, IndexError, ValueError):
        return None


def ref_names():
    p = os.path.join(MARKET, 'reference_stocks_delisted.json')  # names of delisted companies when screener has none
    try:
        return {x['nse_symbol']: x['name'] for x in load(p)['data']['data'] if x.get('nse_symbol')}
    except (TypeError, KeyError):
        return {}


def old_name(sym):
    ov = (load(os.path.join(COMP, sym, 'scr', 'overview.json')) or {}).get('data') or {}
    return ov.get('name') or REF.get(sym) or ''


def name_match(sym, name, last):
    """Unique prefix match of the company's name in the BSE price file nearest (on or before) its last trading date."""
    n = norm(name)
    if len(n) < 5 or not last:
        return None
    for back in range(0, 15):
        rows = bhav(last - dt.timedelta(days=back))
        if rows:
            break
    else:
        return None
    hits = {}
    for code, _, nm in rows:
        k = norm(nm)
        # old files cut names at ~12 characters: a shorter name is complete and must equal ours, a cut one may be a prefix
        if len(k) >= 5 and (n == k or (len(nm) >= 11 and n.startswith(k))):
            hits[code] = nm
    return next(iter(hits.items())) if len(hits) == 1 else None


def build(a):
    os.makedirs(MARKET, exist_ok=True)
    REF.update(ref_names())
    eqf = os.path.join(MARKET, f'EQUITY_L_{dt.date.today():%Y%m%d}.csv')
    if not os.path.exists(eqf):
        if not curl(EQL, eqf, 10000):
            sys.exit('EQUITY_L.csv download failed')
    nse = [{k.strip(): v.strip() for k, v in r.items()} for r in csv.DictReader(open(eqf, encoding='utf-8-sig'))]
    today = dt.date.today()
    by_isin, days = {}, []  # union of the last 5 full price files: thinly traded scrips miss some days
    for back in range(0, 20):
        rows = bhav(today - dt.timedelta(days=back))
        if rows and len(rows) > 1000:
            days.append(today - dt.timedelta(days=back))
            for c, i, n in rows:
                if i:
                    by_isin.setdefault(i, (c, n))
            if len(days) == 5:
                break
    if not days:
        sys.exit('no BSE price file with over 1000 rows in the last 20 days')
    bd = days[0]
    out, seen, stats = [], set(), {}
    for r in nse:
        sym, isin = r['SYMBOL'], r['ISIN NUMBER']
        c, n = by_isin.get(isin, ('', ''))
        out.append([sym, isin, c, n, 'isin' if c else 'unmatched'])
        seen.add(sym)
    others = sorted(os.path.basename(d) for d in glob.glob(os.path.join(COMP, '*')) if os.path.basename(d) not in seen)
    if a.syms:
        keep = set(a.syms.split(','))
        others = [s for s in others if s in keep]
    nsename = {r['SYMBOL']: r['NAME OF COMPANY'] for r in nse}
    for sym in others:
        if sym.isdigit():
            out.append([sym, '', sym, '', 'numeric'])
            continue
        isin = scr_isin(sym)
        c, n = by_isin.get(isin, ('', '')) if isin else ('', '')
        if c:
            out.append([sym, isin, c, n, 'scr-isin'])
            continue
        last = last_trade(sym)
        hit = name_match(sym, old_name(sym), last) if last and (bd - last).days > 30 else None
        out.append([sym, isin, hit[0] if hit else '', hit[1] if hit else '', 'name-match' if hit else 'unmatched'])
    n_by_code = {}
    for r in out:
        if r[4] == 'name-match':
            n_by_code.setdefault(r[2], []).append(r)
    for code, rs in n_by_code.items():  # one code claimed by several symbols: ambiguous, not a match
        if len(rs) > 1:
            for r in rs:
                r[2], r[3], r[4] = '', '', 'unmatched'
    w = csv.writer(open(OUT, 'w', newline='', encoding='utf-8'))
    w.writerow(COLS)
    w.writerows(out)
    for r in out:
        stats[r[4]] = stats.get(r[4], 0) + 1
    print(f'{len(out)} rows (BSE file {bd}): {stats} -> {OUT}')


def lookup(sym, path=OUT):
    """BSE code for an NSE symbol from bse_codes.csv, or None (empty for unmatched). name-match rows are returned too."""
    try:
        for r in csv.DictReader(open(path, encoding='utf-8')):
            if r['nse_symbol'] == sym:
                return r['bse_code'] or None
    except OSError:
        pass
    return None


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--syms', help='comma-separated symbols, e.g. A,B: only these of the data/companies/ folders not in EQUITY_L (every EQUITY_L symbol is still listed; default: every folder)')
    build(ap.parse_args())
