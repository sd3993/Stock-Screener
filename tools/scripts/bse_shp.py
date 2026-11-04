import argparse, csv, datetime as dt, glob, html, json, os, re, subprocess, sys, time
# Old shareholding patterns from BSE (tools/tools.md, BSE "Old data"): one quarter's pattern per request, as HTML, from
#   www.bseindia.com/corporates/ShareholdingPattern.aspx?scripcd=<code>&flag_qtr=1&qtrid=<n>.00&Flag=New
# with plain curl.exe and its default identity (no browser headers; a refusal is recorded, not worked around).
# qtrid = 29 + quarters since Mar 2001 (Mar 2008 = 57); Flag=New is left out before Jun 2006 (qtrid 50). The page has
# data from Mar 2001 to Jun 2022 (qtrid 114); later quarters come back blank (the new-format pattern is browser-only),
# and screener/NSE cover them. Delisted companies are served too.
#   python tools/scripts/bse_shp.py                       # rows of <run>/sample_candidates.csv (sym, start or as_of)
#   python tools/scripts/bse_shp.py --rows FILE           # any CSV with sym and as_of/start (optional bse_code column)
#   python tools/scripts/bse_shp.py --want SYM[:CODE]=YYYY-MM..YYYY-MM ...   # explicit quarter ranges
#   options: --back 12 (quarters before the latest filed one), --gap 1.5 (s between requests), --syms A,B, --plan (count
#            only), --reparse (rebuild the JSON from saved HTML, no requests), --max N (stop after N requests)
# Which quarters: for each (sym, as_of), the latest quarter filed by as_of (quarter end + 21 days, Reg 31 / Clause 35;
# mb_features LAG_SHP) and the --back quarters before it, within Mar 2001 .. Jun 2022.
# BSE code: the rows file's bse_code, else scr/overview.json bse_code, else the symbol itself when numeric (screener names
# BSE-only companies by their code), else a bseplus/AnnualReport/<code>/ link in scr/documents.json; else reported.
# Saves data/companies/<SYM>/bse/shp/<qtrid>_<YYYY-MM>.html (raw page; blank pages too, so they aren't asked again) and
# data/companies/<SYM>/bse/shp/history.json: {fetched_at (IST), via: "bse-curl", url, data: {code, quarters: {YYYY-MM-DD:
# {...}}}} (rebuilt from all the company's saved pages after each run).
# A quarter's record: status ok|blank|mismatch, format pre2006|clause35, total_shares, prom_shares, prom_pct (of all
# shares, A+B+C), prom_pct_page, inst_pct (public institutions sub-total: MFs, banks/FIs, insurers, FIIs/FPIs, VCs),
# fii_pct, mf_pct, public_pct (public shareholding B; pre-2006: 100 - promoters), pledged_shares, pledged_pct_of_promoter,
# pledged_pct_of_total (from Mar 2009; missing before, never 0), warnings. Refused/failed requests aren't saved and are
# asked again on the next run. Per-request log: <run>/bse_shp_log.csv; summary: <run>/bse_shp_summary.md.
# From Dec 2015 BSE serves the new-format filings mapped onto the old table (e.g. FPIs under "Qualified Foreign
# Investor", employee-trust shares left out of the total, so promoter % can differ from NSE's by a few hundredths).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
URL = 'https://www.bseindia.com/corporates/ShareholdingPattern.aspx?scripcd={code}&flag_qtr=1&qtrid={q}.00{flag}'
FIRST, LAST, NEW_FROM, LAG_SHP = 29, 114, 50, 21
MON = {m: i for i, m in enumerate(['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                    'September', 'October', 'November', 'December']) if m}


def qtrid(end):
    return 29 + (end.year - 2001) * 4 + (end.month - 3) // 3


def qend(q):
    k = q - 29
    y, m = 2001 + (k + 0) // 4, 3 + 3 * (k % 4)
    return dt.date(y, m, 30 if m in (6, 9) else 31)


def latest_filed(as_of):
    """The last quarter end whose pattern counts as filed by as_of (quarter end + 21 days)."""
    y, m = as_of.year, as_of.month - as_of.month % 3 or 12
    if as_of.month < 3:
        y -= 1
    e = dt.date(y, m, 30 if m in (6, 9) else 31)
    while e + dt.timedelta(days=LAG_SHP) > as_of:
        y, m = (e.year, e.month - 3) if e.month > 3 else (e.year - 1, 12)
        e = dt.date(y, m, 30 if m in (6, 9) else 31)
    return e


def num(s):
    s = (s or '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return None


def rows_of(page):
    t = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', '', page)
    out = []
    for tr in re.split(r'(?i)</tr>', t):
        cells = [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', c))).strip()
                 for c in re.split(r'(?i)</t[dh]>', tr)]
        while cells and not cells[-1]:
            cells.pop()
        if cells and cells[0]:
            out.append(cells)
    return out


def parse(page, code, end):
    """One quarter's page -> record (status ok|blank|mismatch)."""
    flat = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))
    m = re.search(r'Security Code\s*:\s*(\d+)', flat)
    qe = re.search(r'Quarter Ending\s*:\s*([A-Za-z]+)\s+(\d{4})', flat)
    rows = rows_of(page)
    lab = lambda r: re.sub(r'\s+', ' ', r[0]).strip()
    rec = {'status': 'ok', 'warnings': []}
    if not qe or not any(re.match(r'(Grand Total|Total \(A\)\s*\+\s*\(B\)\s*\+\s*\(C\))', lab(r)) for r in rows):
        return {'status': 'blank'}
    if (m and m.group(1) != str(code)) or (MON.get(qe.group(1)), int(qe.group(2))) != (end.month, end.year):
        return {'status': 'mismatch', 'page': f'{m and m.group(1)} {qe.group(1)} {qe.group(2)}'}
    idx = lambda pat, start=0: next((i for i in range(start, len(rows)) if re.match(pat, lab(rows[i]), re.I)), None)
    if idx(r'Total shareholding of Promoter') is not None:
        rec['format'] = 'clause35'
        A = rows[idx(r'Total shareholding of Promoter')]
        T = rows[idx(r'Total \(A\)\s*\+\s*\(B\)\s*\+\s*\(C\)')]
        total, prom = num(T[2]), num(A[2])
        ic = idx(r'\(C\)')
        c1 = idx(r'\(1\) Promoter', ic) if ic is not None else None
        if c1 is not None and num(rows[c1][2]):
            prom += num(rows[c1][2])
            rec['warnings'].append('promoter shares include depository-receipt shares (C1)')
        ib = idx(r'\(B\)')
        ii = idx(r'\(1\) Institutions', ib or 0)
        isub = idx(r'Sub Total', ii) if ii is not None else None
        inst_rows = rows[ii + 1:isub] if isub is not None else []
        pick = lambda pat: sum(num(r[2]) or 0 for r in inst_rows if re.search(pat, lab(r), re.I))
        rec.update(total_shares=total, prom_shares=prom,
                   prom_pct_page=num(A[5]) if len(A) > 5 else None,
                   inst_shares=num(rows[isub][2]) if isub is not None else None,
                   fii_shares=pick(r'Foreign Institutional|Foreign Portfolio|Qualified\s+Foreign'),
                   mf_shares=pick(r'Mutual'))
        PB = rows[idx(r'Total Public shareholding')] if idx(r'Total Public shareholding') is not None else None
        rec['public_pct'] = round(100 * num(PB[2]) / total, 2) if PB and total else None
        if len(A) >= 8 and num(A[6]) is not None:
            rec['pledged_shares'] = num(A[6])
            rec['pledged_pct_page'] = num(A[7])
    else:
        rec['format'] = 'pre2006'
        ip, inp, ig = idx(r"Promoter'?s'? Holding"), idx(r"Non[- ]?Promoter"), idx(r'Grand Total')
        if None in (ip, inp, ig):
            return {'status': 'blank', 'warnings': ['unrecognised layout']}
        subs = [i for i in range(ip, inp) if lab(rows[i]).lower().startswith('sub total')]
        total = num(rows[ig][1])
        prom = num(rows[subs[-1]][1]) if subs else None
        ii = idx(r'Institutional Investors', inp)
        isub = idx(r'Sub Total', ii) if ii is not None else None
        inst_rows = rows[ii + 1:isub] if isub is not None else []
        pick = lambda pat: sum(num(r[1]) or 0 for r in inst_rows if re.search(pat, lab(r), re.I))
        rec.update(total_shares=total, prom_shares=prom, prom_pct_page=num(rows[subs[-1]][2]) if subs else None,
                   inst_shares=num(rows[isub][1]) if isub is not None else None,
                   fii_shares=pick(r'FII|Foreign Institutional'), mf_shares=pick(r'Mutual'))
        rec['public_pct'] = round(100 - 100 * prom / total, 2) if prom is not None and total else None
    total = rec['total_shares']
    if not total or rec['prom_shares'] is None:
        return {'status': 'blank', 'warnings': ['no totals']}
    pct = lambda k: round(100 * rec[k] / total, 2) if rec.get(k) is not None else None
    rec['prom_pct'], rec['inst_pct'], rec['fii_pct'], rec['mf_pct'] = (pct('prom_shares'), pct('inst_shares'),
                                                                        pct('fii_shares'), pct('mf_shares'))
    if 'pledged_shares' in rec:
        rec['pledged_pct_of_promoter'] = round(100 * rec['pledged_shares'] / rec['prom_shares'], 2) if rec['prom_shares'] else 0.0
        rec['pledged_pct_of_total'] = round(100 * rec['pledged_shares'] / total, 2)
    if rec['prom_pct_page'] is not None and abs(rec['prom_pct_page'] - rec['prom_pct']) > 0.05:
        rec['warnings'].append(f"page promoter % {rec['prom_pct_page']} vs shares/total {rec['prom_pct']}")
    for k in ('inst_shares', 'fii_shares', 'mf_shares'):
        rec.pop(k, None)
    if not rec['warnings']:
        rec.pop('warnings')
    return rec


def load(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return None


_CODES = {}


def csv_code(sym):
    if not _CODES:
        try:
            _CODES.update({r['nse_symbol']: r['bse_code'] for r in csv.DictReader(
                open(os.path.join('data', 'market', 'bse_codes.csv'), encoding='utf-8'))})
        except OSError:
            _CODES['-'] = ''
    return _CODES.get(sym) or None


def bse_code(sym, root, given=None):
    if given:
        return str(given)
    ov = ((load(os.path.join(root, sym, 'scr', 'overview.json')) or {}).get('data') or {})
    if str(ov.get('bse_code') or '').strip().isdigit():  # screener sometimes stores junk there ("data", "All")
        return str(ov['bse_code']).strip()
    c = csv_code(sym)  # data/market/bse_codes.csv (bse_codes.py): NSE-ISIN join, name-match rows are for review
    if c:
        return c
    if sym.isdigit():
        return sym
    p = os.path.join(root, sym, 'scr', 'documents.json')
    if os.path.exists(p):
        m = re.search(r'bseplus/AnnualReport/(\d{6})/', open(p, encoding='utf-8').read())
        if m:
            return m.group(1)
    return None


def fetch(url, out, timeout=60):
    """curl.exe with its default identity -> (http code, bytes); the file is written only on 200."""
    tmp = out + '.part'
    try:
        r = subprocess.run(['curl.exe', '-s', '-m', str(timeout), '-o', tmp, '-w', '%{http_code}', url],
                           capture_output=True, text=True, timeout=timeout + 15)
        code = int(r.stdout.strip() or 0)
    except (subprocess.TimeoutExpired, ValueError):
        code = 0
    if code == 200 and os.path.exists(tmp):
        os.replace(tmp, out)
        return code, os.path.getsize(out)
    if os.path.exists(tmp):
        os.remove(tmp)
    return code, 0


def write_json(sym, root, code):
    """Rebuild the company's history.json from all its saved pages; fetched_at = the newest page's save time."""
    d = os.path.join(root, sym, 'bse', 'shp')
    qs, newest = {}, 0
    for f in sorted(glob.glob(os.path.join(d, '*_*.html'))):
        q = int(os.path.basename(f).split('_')[0])
        qs[qend(q).isoformat()] = dict(qtrid=q, **parse(open(f, encoding='utf-8', errors='replace').read(), code, qend(q)))
        newest = max(newest, os.path.getmtime(f))
    if qs:
        json.dump({'fetched_at': dt.datetime.fromtimestamp(newest, IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'bse-curl',
                   'url': URL.format(code='<code>', q='<qtrid>', flag='[&Flag=New]'), 'data': {'code': code, 'quarters': qs}},
                  open(os.path.join(d, 'history.json'), 'w', encoding='utf-8'), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows')
    ap.add_argument('--want', nargs='*')
    ap.add_argument('--back', type=int, default=12)
    ap.add_argument('--gap', type=float, default=1.5)
    ap.add_argument('--syms')
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--reparse', action='store_true')
    ap.add_argument('--max', type=int, default=0)
    ap.add_argument('--companies', default=os.path.join('data', 'companies'))
    a = ap.parse_args()
    root = a.companies
    if a.reparse:  # every company with saved pages (or --syms), no requests
        syms = a.syms.split(',') if a.syms else [os.path.basename(os.path.dirname(os.path.dirname(p)))
                                                   for p in glob.glob(os.path.join(root, '*', 'bse', 'shp'))]
        for sym in sorted(syms):
            write_json(sym, root, bse_code(sym, root))
        print(f'{len(syms)} companies re-parsed')
        return
    need, codes = {}, {}  # sym -> set of qtrids
    if a.want:
        for w in a.want:
            m = re.match(r'([^:=]+)(?::(\d+))?=(\d{4})-(\d{2})\.\.(\d{4})-(\d{2})$', w)
            if not m:
                sys.exit(f'bad --want {w}: SYM[:CODE]=YYYY-MM..YYYY-MM')
            sym = m.group(1)
            q0 = qtrid(dt.date(int(m.group(3)), int(m.group(4)), 1))
            q1 = qtrid(dt.date(int(m.group(5)), int(m.group(6)), 1))
            need.setdefault(sym, set()).update(range(max(q0, FIRST), min(q1, LAST) + 1))
            codes[sym] = m.group(2)
    if not a.want or a.rows:
        D = hist_dir()
        for r in csv.DictReader(open(a.rows or os.path.join(D, 'sample_candidates.csv'), encoding='utf-8')):
            as_of = (r.get('as_of') or r.get('start') or '')[:10]
            if not as_of:
                continue
            q0 = qtrid(latest_filed(dt.date.fromisoformat(as_of)))
            need.setdefault(r['sym'], set()).update(q for q in range(q0 - a.back, q0 + 1) if FIRST <= q <= LAST)
            codes.setdefault(r['sym'], r.get('bse_code'))
    if a.syms:
        keep = set(a.syms.split(','))
        need = {k: v for k, v in need.items() if k in keep}
    run = hist_dir()
    nocode, todo = [], []
    for sym in sorted(need):
        code = bse_code(sym, root, codes.get(sym))
        if not code:
            nocode.append(sym)
            continue
        d = os.path.join(root, sym, 'bse', 'shp')
        for q in sorted(need[sym]):
            f = os.path.join(d, f'{q}_{qend(q):%Y-%m}.html')
            if not os.path.exists(f):
                todo.append((sym, code, q, f))
        codes[sym] = code
    nq = sum(len(v) for v in need.values())
    print(f'{len(need)} companies, {nq} quarters wanted, {len(todo)} to fetch, {len(nocode)} without a BSE code'
          + (f': {" ".join(nocode)}' if nocode else ''), flush=True)
    if a.plan:
        print(f'estimated {len(todo) * (a.gap + 0.5) / 3600:.1f} h at ~{a.gap + 0.5:.1f} s a request (tested: 1.95 s at --gap 1.5)')
        return
    logp = os.path.join(run, 'bse_shp_log.csv')
    newlog = not os.path.exists(logp)
    log = open(logp, 'a', newline='', encoding='utf-8')
    lw = csv.writer(log)
    if newlog:
        lw.writerow(['time', 'sym', 'code', 'qtrid', 'quarter', 'http', 'bytes', 'status'])
    t0, n, gap, fails, stats = time.time(), 0, a.gap, 0, {}
    touched = set()
    for sym, code, q, f in todo:
        if a.max and n >= a.max:
            break
        os.makedirs(os.path.dirname(f), exist_ok=True)
        url = URL.format(code=code, q=q, flag='&Flag=New' if q >= NEW_FROM else '')
        for attempt in range(3):
            if n:
                time.sleep(gap)
            n += 1
            http, size = fetch(url, f)
            if http == 200:
                fails, gap = 0, max(a.gap, gap * 0.9)
                st = parse(open(f, encoding='utf-8', errors='replace').read(), code, qend(q))['status']
                break
            fails += 1
            st = 'refused' if http in (401, 403, 429) else f'error'
            gap = min(60, gap * 2)
            if http in (401, 403):
                break  # a refusal is recorded and left, never worked around
        lw.writerow([dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), sym, code, q, f'{qend(q):%Y-%m}', http, size, st])
        log.flush()
        stats[st] = stats.get(st, 0) + 1
        touched.add(sym)
        if fails >= 20:
            print('20 failed requests in a row: stopping (BSE refusing or down); re-run later to resume', flush=True)
            break
        if n % 100 == 0:
            print(f'{n} requests, {time.time() - t0:.0f}s, {stats}', flush=True)
    log.close()
    for sym in sorted(touched):
        write_json(sym, root, codes[sym])
    now = dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
    lines = [f'# bse_shp.py run {now}', '',
             f'- {len(need)} companies, {nq} quarters wanted, {len(todo)} not yet saved at start; {n} requests in '
             f'{time.time() - t0:.0f}s: {stats}',
             f'- without a BSE code ({len(nocode)}): {" ".join(nocode) or "none"}']
    open(os.path.join(run, 'bse_shp_summary.md'), 'a', encoding='utf-8').write('\n'.join(lines) + '\n\n')
    print('\n'.join(lines[2:]))


if __name__ == '__main__':
    main()
