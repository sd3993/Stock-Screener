import argparse, bisect, csv, datetime as dt, glob, os, sys
# Multibagger study, step 1 (process/historical/s1_universe.md): from every saved chart history (data/companies/*/scr/history.json, by
# mb_history.py), the price and market-cap multiples over 2-, 3-, 5-, 7- and 10-year windows starting at each quarter end
# from Mar 2006, with the starting market cap, P/E and TTM EPS/sales, and the peak multiple inside the window (for fallen
# winners), and what could be seen at the start: P/E and its own 5-year median, TTM EPS and sales growth over 1 and 3
# years, and the prior 1-year price return. Writes runs/historical/<date>/outcomes.csv (or --out FILE).
#   python -I tools/scripts/mb_outcomes.py [--out FILE] [--syms A,B] [--companies DIR]
# Point in time: start figures come from mb_features.py's Company (one rule for both scripts): TTM EPS and sales as filed
# by the start (a chart step stamped on a quarter end counts from its filing lag), P/E = price / that EPS, and its 5-year
# median from the weekly P/Es as filed. Market cap = market-cap-to-sales on the last weekly point x the TTM sales screener
# divided by on that same date (Company.mcap), at the window start and end alike; it is a market figure, needs no lag.
# Prices and the price multiples (px_*, pxpeak_*) are unchanged by this (the price series has no filing lag).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir
from mb_features import Company, add_years, cagr

YEARS = (2, 3, 5, 7, 10)
ap = argparse.ArgumentParser()
ap.add_argument('--out')
ap.add_argument('--syms')
ap.add_argument('--companies', default=os.path.join('data', 'companies'))
a = ap.parse_args()
today = dt.date.today()
starts = [dt.date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m]) for y in range(2006, today.year + 1) for m in (3, 6, 9, 12)
          if dt.date(y, m, 28) < today]


def peak(s, a_, b):
    vals = [v for t, v in s if a_ < t <= b]
    return max(vals) if vals else None


def r1(x, n=1):
    return None if x is None else round(x, n)


rows = []
syms = a.syms.split(',') if a.syms else sorted(os.path.basename(os.path.dirname(os.path.dirname(fn)))
                                               for fn in glob.glob(os.path.join(a.companies, '*', 'scr', 'history.json')))
for sym in syms:
    c = Company(sym, a.companies, chart_only=True)
    px = c.px
    if len(px) < 10:
        continue
    last = px[-1][0]
    for st in starts:
        p0 = c.px_at(st)
        if p0 is None or p0 <= 0:
            continue
        e0, s0 = c.eps.lookup(st), c.sales.lookup(st)
        e1, s1 = c.eps.lookup(add_years(st, -1)), c.sales.lookup(add_years(st, -1))
        e3, s3 = c.eps.lookup(add_years(st, -3)), c.sales.lookup(add_years(st, -3))
        k, lo = bisect.bisect_right(c.pxd, st), bisect.bisect_right(c.pxd, add_years(st, -5))
        pes = sorted(v for v in c.pe_w[lo:k] if v is not None)
        m0 = c.mcap(st)[0]
        pb = c.px_at(add_years(st, -1))
        row = {'sym': sym, 'start': st.isoformat(), 'px0': round(p0, 2), 'mc0': r1(m0),
               'pe0': r1(p0 / e0) if e0 and e0 > 0 else None, 'pe_med5': r1(pes[len(pes) // 2]) if len(pes) >= 20 else None,
               'eps0': e0, 'sales0': s0,
               'eps_g1': r1((e0 / e1 - 1) * 100) if e0 is not None and e1 and e1 > 0 else None,
               'eps_g3': r1(cagr(e0, e3, 3)), 'sales_g1': r1(cagr(s0, s1, 1)), 'sales_g3': r1(cagr(s0, s3, 3)),
               'px_ret1': round(p0 / pb, 3) if pb else None, 'last_price_date': last.isoformat()}
        for n in YEARS:
            end = add_years(st, n)
            if end > last:  # delisted, or not yet n years: the window is incomplete
                continue
            p1, m1 = c.px_at(end), c.mcap(end)[0]
            row[f'px_{n}y'] = round(p1 / p0, 3) if p1 else None
            row[f'mc_{n}y'] = round(m1 / m0, 3) if m0 and m1 else None
            pk = peak(px, st, end)
            row[f'pxpeak_{n}y'] = round(pk / p0, 3) if pk else None
        rows.append(row)
keys = ['sym', 'start', 'px0', 'mc0', 'pe0', 'pe_med5', 'eps0', 'sales0', 'eps_g1', 'eps_g3', 'sales_g1', 'sales_g3', 'px_ret1',
        'last_price_date'] + \
       [f'{k}_{n}y' for n in YEARS for k in ('px', 'mc', 'pxpeak')]
out = a.out or os.path.join(hist_dir(), 'outcomes.csv')
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
print(f'{len({r["sym"] for r in rows})} companies, {len(rows)} company-quarters -> {out}')
