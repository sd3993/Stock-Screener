import bisect, csv, datetime as dt, glob, json, os, sys
# Task 2, phase 1 (studies/multibaggers/plan.md): from every saved chart history (data/companies/*/scr/history.json, by
# mb_history.py), the price and market-cap multiples over 2-, 3-, 5-, 7- and 10-year windows starting at each quarter end
# from Mar 2006, with the starting market cap, P/E and TTM EPS/sales, and the peak multiple inside the window (for fallen
# winners), and what could be seen at the start: P/E and its own 5-year median, TTM EPS and sales growth over 1 and 3
# years, and the prior 1-year price return. Market cap = market-cap-to-sales x TTM sales on the same date. Writes studies/multibaggers/outcomes.csv.
#   python tools/scripts/mb_outcomes.py
YEARS = (2, 3, 5, 7, 10)
today = dt.date.today()
starts = [dt.date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m]) for y in range(2006, today.year + 1) for m in (3, 6, 9, 12)
          if dt.date(y, m, 28) < today]

def series(pairs):
    """[(date, float)] sorted, from chart values [[YYYY-MM-DD, value, ...], ...]; empty values dropped."""
    out = []
    for p in pairs or []:
        try:
            out.append((dt.date.fromisoformat(p[0]), float(p[1])))
        except (TypeError, ValueError, IndexError):
            pass
    return sorted(out)

def at(s, d, max_gap=40):
    """Value on or before d (within max_gap days), else None."""
    i = bisect.bisect_right([x[0] for x in s], d) - 1
    return s[i][1] if i >= 0 and (d - s[i][0]).days <= max_gap else None

def peak(s, a, b):
    vals = [v for t, v in s if a < t <= b]
    return max(vals) if vals else None

def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)

rows = []
for fn in glob.glob(os.path.join('data', 'companies', '*', 'scr', 'history.json')):
    env = json.load(open(fn, encoding='utf-8'))
    sym, h = env['args']['symbol'], env['data']
    px = series((h.get('price') or {}).get('datasets', {}).get('Price'))
    if len(px) < 10:
        continue
    pe = series((h.get('pe') or {}).get('datasets', {}).get('Price to Earning'))
    eps = series((h.get('pe') or {}).get('datasets', {}).get('EPS'))
    mcs = series((h.get('mcap_sales') or {}).get('datasets', {}).get('Market Cap to Sales'))
    sales = series((h.get('mcap_sales') or {}).get('datasets', {}).get('Sales'))
    def mcap(d):
        r, s = at(mcs, d), at(sales, d, max_gap=200)  # TTM sales change once a quarter
        return r * s if r is not None and s else None
    last = px[-1][0]
    for st in starts:
        p0 = at(px, st)
        if p0 is None or p0 <= 0:
            continue
        e0, s0 = at(eps, st, 200), at(sales, st, 200)
        def growth(series_, now, yrs):  # CAGR of a TTM series over the yrs before the start (None if not positive)
            then = at(series_, add_years(st, -yrs), 200)
            return round(((now / then) ** (1 / yrs) - 1) * 100, 1) if now and then and now > 0 and then > 0 else None
        pes = [v for t, v in pe if add_years(st, -5) < t <= st and v and v > 0]
        pe_med5 = sorted(pes)[len(pes) // 2] if len(pes) >= 20 else None
        e1 = at(eps, add_years(st, -1), 200)
        row = {'sym': sym, 'start': st.isoformat(), 'px0': round(p0, 2), 'mc0': round(mcap(st), 1) if mcap(st) else None,
               'pe0': at(pe, st), 'pe_med5': pe_med5, 'eps0': e0, 'sales0': s0,
               'eps_g1': round((e0 / e1 - 1) * 100, 1) if e0 and e1 and e1 > 0 else None,
               'eps_g3': growth(eps, e0, 3), 'sales_g3': growth(sales, s0, 3), 'sales_g1': growth(sales, s0, 1),
               'px_ret1': round(p0 / at(px, add_years(st, -1)) , 3) if at(px, add_years(st, -1)) else None,
               'last_price_date': last.isoformat()}
        for n in YEARS:
            end = add_years(st, n)
            if end > last:  # delisted, or not yet n years: the window is incomplete
                continue
            p1, m0, m1 = at(px, end), mcap(st), mcap(end)
            row[f'px_{n}y'] = round(p1 / p0, 3) if p1 else None
            row[f'mc_{n}y'] = round(m1 / m0, 3) if m0 and m1 else None
            pk = peak(px, st, end)
            row[f'pxpeak_{n}y'] = round(pk / p0, 3) if pk else None
        rows.append(row)
keys = ['sym', 'start', 'px0', 'mc0', 'pe0', 'pe_med5', 'eps0', 'sales0', 'eps_g1', 'eps_g3', 'sales_g1', 'sales_g3', 'px_ret1',
        'last_price_date'] + \
       [f'{k}_{n}y' for n in YEARS for k in ('px', 'mc', 'pxpeak')]
out = os.path.join('studies', 'multibaggers', 'outcomes.csv')
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
print(f'{len({r["sym"] for r in rows})} companies, {len(rows)} company-quarters -> {out}')
