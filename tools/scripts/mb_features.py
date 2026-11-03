import argparse, bisect, calendar, csv, datetime as dt, json, os, statistics, sys, time
# Multibagger study, step 4 (process/historical/s4_backtest.md, step 1): point-in-time features for any list of (sym, as_of)
# rows, from each company's saved screener data (data/companies/<SYM>/scr/: history.json from S1; statements, quarterly and
# shareholding from the S2/S3 fetch). No fetching. Writes features.csv (one row per input row: sym, as_of, group, horizon,
# the features, the bases and periods used) and features_coverage.md (share of rows with each feature, by start period).
#   python -I tools/scripts/mb_features.py                       # sample.csv of the newest study run
#   python -I tools/scripts/mb_features.py --rows FILE           # any CSV with sym and as_of (or start); other columns kept
#   python -I tools/scripts/mb_features.py --candidates          # sample_candidates.csv
#   python -I tools/scripts/mb_features.py --market [--from 2006] [--chart-only]   # every (sym, start) in outcomes.csv
#   options: --out FILE (default <run>/features.csv; coverage beside it), --syms A,B (limit), --companies DIR
#
# Point in time (README "What a pattern must pass", 1): a figure is used only once it counts as filed by as_of.
#   - quarter results: quarter end + 45 days; the fiscal year's last quarter and annual P&L, balance sheet and ratios: + 60;
#     COVID extensions: periods ending Mar 2020 + 120, Jun 2020 + 75, Mar 2021 + 90 (SEBI relaxations; conservative);
#   - annual cash flow: + 60 for years ending from Sep 2019 (SEBI made the cash-flow statement part of the half-year
#     results from H1 FY20); earlier years only in the annual report: + 180;
#   - shareholding: the NSE filing date where saved (shp_history, shareholding_nse), else quarter end + 21 (Reg 31;
#     Clause 35 before Dec 2015); quarters older than screener's and NSE's come from BSE's old patterns
#     (bse/shp/history.json, bse_shp.py), which also fill fields those sources lack; src_shp_via names the sources used;
#   - chart TTM EPS and sales (history.json): screener moves them on the results date in most years, but in some years
#     (e.g. 2006-10, 2014-16 for many companies) the change is stamped on the quarter end itself, before any filing. A change
#     stamped within 6 days of a quarter end counts from that quarter end + 45 (+ 60 for the fiscal year's last quarter);
#     other changes from their own date. P/E is recomputed as price / that EPS (so it differs from screener's chart P/E
#     and from outcomes.csv's pe0 where the stamp was early). Market cap = market-cap-to-sales on the last weekly point x
#     the TTM sales screener had on that same point's date (Company.mcap; mb_outcomes.py uses the same Company, so its start
#     figures follow these rules too). pe_med5 needs 156+ weekly positive P/Es in the 5 years (pe_med5_wks).
# Shares: shares_chg1/3 from chart-implied shares (market cap / adjusted price, 13-week mean), so splits and bonuses don't
#   count; ~1-2% noise from the one-decimal market-cap-to-sales. eq_cap_chg3 (equity capital) rises with bonuses too.
# Lenders (P&L with 'Financing Profit'): opm is the financing margin; de, int_cover, debt_ebitda, roce, cash conversion
#   and fscore8 are left empty (rule 4: borrowing is the business); roa, gnpa, nnpa are added. int_cover = 999 means
#   no interest with a positive profit.
# Basis: annual and quarterly statements use consolidated when it has the latest period filed by as_of, else standalone,
#   and all multi-year figures for that row use the same basis (missing if that basis lacks the years). Chart series are
#   consolidated where screener has them, else standalone (mb_history.py). Missing stays empty, never 0.
# Restatement: statements are today's restated figures. stmt_gap_fy lists the fiscal years used whose statement sales
#   differ by more than 10% from the chart's TTM sales after that year's results (restated, merged, or a basis gap: before
#   FY20 many companies filed only standalone quarterly results, which the chart's TTM then follows).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir

LAG_Q, LAG_Q4, LAG_SHP, LAG_CF_AR = 45, 60, 21, 180
OVERRIDE = {(2020, 3): 120, (2020, 6): 75, (2021, 3): 90}
CF_WITH_RESULTS = dt.date(2019, 9, 30)
MON = {m: i for i, m in enumerate(calendar.month_abbr) if m}


def month_end(y, m):
    return dt.date(y, m, calendar.monthrange(y, m)[1])


def parse_period(lbl):
    """'Mar 2015' / 'Mar 2015 15m' / '31-MAR-2026' -> (date, months)."""
    p = lbl.replace('-', ' ').split()
    if len(p) >= 3 and p[0].isdigit():  # 31 MAR 2026
        return month_end(int(p[2]), MON[p[1].title()]), 12
    months = int(p[2][:-1]) if len(p) > 2 and p[2].endswith('m') else 12
    return month_end(int(p[1]), MON[p[0][:3].title()]), months


def lag(end, q4):
    return OVERRIDE.get((end.year, end.month), LAG_Q4 if q4 else LAG_Q)


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def fnum(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def rnd(x, n=2):
    return None if x is None else round(x, n)


def cagr(a, b, yrs):
    return (a / b) ** (1 / yrs) * 100 - 100 if a is not None and b is not None and a > 0 and b > 0 else None


def ratio(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def load(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh).get('data')
    except (OSError, ValueError):
        return None


def series(pairs):
    out = []
    for p in pairs or []:
        try:
            v = float(p[1])
            out.append((dt.date.fromisoformat(p[0]), v))
        except (TypeError, ValueError, IndexError):
            pass
    return sorted(out)


class Step:
    """A chart TTM series (EPS or sales) as filed: lookup(d) gives the value public on d."""

    def __init__(self, pts, fy_month):
        self.raw = [t for t, _ in pts]
        steps, prev = [], None
        for t, v in pts:
            if v != prev:
                eff = t
                for q in (month_end(t.year, t.month), month_end((t - dt.timedelta(days=10)).year,
                                                                (t - dt.timedelta(days=10)).month)):
                    if q.month in (3, 6, 9, 12) and -6 <= (t - q).days <= 5:
                        eff = q + dt.timedelta(days=lag(q, q.month == fy_month))
                        break
                steps.append((eff, t, v))
            prev = v
        self.steps = sorted(steps)  # by effective date
        self.eff = [s[0] for s in self.steps]
        self.redated = sum(1 for e, t, _ in steps if e != t)
        self.best, b = [], None  # best[k]: value of the latest period among steps[:k + 1]
        for s in self.steps:
            b = s if b is None or s[1] > b[1] else b
            self.best.append(b[2])

    def lookup(self, d, max_gap=400):  # some series are annual-only for years
        i = bisect.bisect_right(self.raw, d) - 1
        if i < 0 or (d - self.raw[i]).days > max_gap:
            return None
        k = bisect.bisect_right(self.eff, d)
        if not k:
            return None
        return self.best[k - 1]  # the latest period already filed


class Table:
    """One statement (annual or quarterly), chosen basis: {period_end: {label: value}}, months per period."""

    def __init__(self, data):
        self.cols, self.months = {}, {}
        if not data or not data.get('rows'):
            return
        labels = data.get('years') or data.get('quarters') or []
        for j, lbl in enumerate(labels):
            try:
                end, m = parse_period(lbl)
            except (KeyError, ValueError, IndexError):
                continue
            col = {}
            for r in data['rows']:
                vals = r.get('values') or []
                if j < len(vals) and r['label'] not in col:  # first row wins (ratios repeat 'ROE %')
                    col[r['label']] = fnum(vals[j])
            self.cols[end], self.months[end] = col, m

    def get(self, end, *labels):
        c = self.cols.get(end) or {}
        for lb in labels:
            if c.get(lb) is not None:
                return c[lb]
        return None


class Company:
    def __init__(self, sym, root, chart_only=False):
        self.sym = sym
        d = os.path.join(root, sym, 'scr')
        h = load(os.path.join(d, 'history.json')) or {}
        self.chart_basis = 'consolidated' if (h.get('pe') or {}).get('consolidated') else 'standalone' if h else ''
        ds = lambda k, n: series(((h.get(k) or {}).get('datasets') or {}).get(n))
        self.px, self.vol = ds('price', 'Price'), ds('price', 'Volume')
        self.mcs, sales_raw = ds('mcap_sales', 'Market Cap to Sales'), ds('mcap_sales', 'Sales')
        self.sales_raw, self.sales_raw_d = sales_raw, [t for t, _ in sales_raw]
        self.pxd = [t for t, _ in self.px]
        self.st = {}
        # chart-only still reads the P&L (where saved) for the fiscal year end, which sets the Q4 lag of chart steps
        for st in (('profit_loss',) if chart_only else ('profit_loss', 'balance_sheet', 'cash_flow', 'ratios', 'quarterly')):
            self.st[st] = {'consolidated': Table(load(os.path.join(d, st + '.json'))),
                           'standalone': Table(load(os.path.join(d, st + '_standalone.json')))}
        pl = self.st.get('profit_loss', {})
        months = [e.month for b in ('consolidated', 'standalone') for e, m in (pl[b].months.items() if pl else []) if m == 12]
        self.fy_month = max(set(months), key=months.count) if months else 3
        self.eps = Step(ds('pe', 'EPS'), self.fy_month)
        self.sales = Step(sales_raw, self.fy_month)
        # weekly P/E as filed, for the 5-year median
        self.pe_w = []
        for t, p in self.px:
            e = self.eps.lookup(t)
            self.pe_w.append(p / e if e and e > 0 and p > 0 else None)
        self.shp = {} if chart_only else self.shareholding(d)

    def shareholding(self, d):
        """{quarter_end: {filed, prom, pledge, inst}}: NSE filings (with filing dates) over screener's 12 quarters."""
        q = {}
        s = load(os.path.join(d, 'shareholding.json')) or {}
        rows = {r['label']: r['values'] for r in s.get('rows') or []}
        for j, lbl in enumerate(s.get('quarters') or []):
            try:
                end, _ = parse_period(lbl)
            except (KeyError, ValueError, IndexError):
                continue
            g = lambda k: fnum(rows[k][j]) if j < len(rows.get(k) or []) else None
            fii, dii = g('FIIs'), g('DIIs')
            q[end] = {'filed': end + dt.timedelta(days=LAG_SHP), 'prom': g('Promoters'), 'pledge': None,
                      'inst': fii + dii if fii is not None and dii is not None else None, 'src': 'screener'}
        for r in (load(os.path.join(d, 'shareholding_nse.json')) or {}).get('rows') or []:
            try:
                end, _ = parse_period(r['date'])
                filed = dt.datetime.strptime(r['submissionDate'], '%d-%b-%Y').date()
            except (KeyError, ValueError, TypeError):
                continue
            e = q.setdefault(end, {'inst': None, 'pledge': None})
            if fnum(r.get('pr_and_prgrp')) is not None:
                e.update(filed=filed, prom=fnum(r['pr_and_prgrp']), src='nse')
        for r in (load(os.path.join(d, 'shp_history.json')) or {}).get('rows') or []:
            try:
                end, _ = parse_period(r['quarter_end'])
                filed = dt.datetime.strptime(r['filed'], '%d-%b-%Y').date()
            except (KeyError, ValueError, TypeError):
                continue
            e = q.setdefault(end, {'inst': None, 'prom': None, 'src': 'nse'})
            e['filed'] = min(filed, e.get('filed') or filed)
            if fnum(r.get('promoter_pct')) is not None and e.get('prom') is None:
                e['prom'] = fnum(r['promoter_pct'])
            e['pledge'] = fnum(r.get('pledged_pct_of_promoter'))
        # BSE's old patterns (bse_shp.py; Mar 2001 - Jun 2022): fill quarters and fields the sources above lack
        bse = (load(os.path.join(os.path.dirname(d), 'bse', 'shp', 'history.json')) or {}).get('quarters') or {}
        for k, r in bse.items():
            if r.get('status') != 'ok':
                continue
            end = dt.date.fromisoformat(k)
            v = {'prom': fnum(r.get('prom_pct')), 'inst': fnum(r.get('inst_pct')),
                 'pledge': fnum(r.get('pledged_pct_of_promoter'))}
            if end not in q:
                q[end] = dict(v, filed=end + dt.timedelta(days=LAG_SHP), src='bse')
                continue
            e = q[end]
            add = [x for x in v if e.get(x) is None and v[x] is not None]
            for x in add:
                e[x] = v[x]
            if add:
                e['src'] = (e.get('src') or '') + '+bse'
        return q

    # ---------- point-in-time helpers ----------
    def mcap(self, d, gap=40):
        """(market cap in crore, chart date): market-cap-to-sales on the last weekly point on or before d (within gap days)
        x the TTM sales screener divided by on that same date. Not the sales on d: a quarter-end-stamped sales step after
        the last weekly point would mix two figures (mb_outcomes.py did, before 4 Nov 2026)."""
        i = bisect.bisect_right([t for t, _ in self.mcs], d) - 1
        if i < 0 or (d - self.mcs[i][0]).days > gap:
            return None, None
        td, r = self.mcs[i]
        j = bisect.bisect_right(self.sales_raw_d, td) - 1
        if r is None or j < 0 or (td - self.sales_raw_d[j]).days > 400 or not self.sales_raw[j][1]:
            return None, td
        return r * self.sales_raw[j][1], td

    def px_at(self, d, gap=40):
        i = bisect.bisect_right(self.pxd, d) - 1
        return self.px[i][1] if i >= 0 and (d - self.px[i][0]).days <= gap else None

    def shares(self, d):
        """Shares (crore) implied by the chart: market cap / price, averaged over the 13 weeks to d, which evens out the
        one-decimal rounding of market cap to sales. Prices are adjusted for splits and bonuses, so this counts in today's
        share units and its change is issuance or buyback only (statement EPS isn't adjusted consistently across years)."""
        md = [t for t, _ in self.mcs]
        vals = []
        for t, r in self.mcs[bisect.bisect_right(md, d - dt.timedelta(days=91)):bisect.bisect_right(md, d)]:
            j = bisect.bisect_right(self.sales_raw_d, t) - 1
            p = self.px_at(t, 7)
            if r and p and j >= 0 and (t - self.sales_raw_d[j]).days <= 400:
                vals.append(r * self.sales_raw[j][1] / p)
        return sum(vals) / len(vals) if len(vals) >= 4 else None

    def basis(self, st, as_of):
        """(basis, [period ends filed by as_of, newest first]) for a statement."""
        best = None
        for b in ('consolidated', 'standalone'):
            t = self.st[st][b]
            ends = sorted((e for e, c in t.cols.items() if any(v is not None for v in c.values())
                           and e + dt.timedelta(days=self.avail_lag(st, e, t.months[e])) <= as_of), reverse=True)
            if ends and (best is None or ends[0] > best[1][0]):
                best = (b, ends)
        return best or ('', [])

    def avail_lag(self, st, end, months):
        if st == 'quarterly':
            return lag(end, end.month == self.fy_month)
        if st == 'cash_flow' and end < CF_WITH_RESULTS:
            return max(LAG_CF_AR, lag(end, True))
        if st == 'balance_sheet' and end.month != self.fy_month:
            return lag(end, False)  # half-year balance sheet, filed with Q2 results
        return lag(end, True)


def yearly(ends, months, n):
    """The newest n+1 fiscal-year ends, each 12 months apart (None where the chain breaks)."""
    out = [ends[0]] if ends else []
    for e in ends[1:]:
        if len(out) > n:
            break
        if months.get(e, 12) == 12 and months.get(out[-1], 12) == 12 and 330 <= (out[-1] - e).days <= 400:
            out.append(e)
        else:
            break
    return out


def features(c, as_of, chart_only=False):
    f, src = {}, {}
    # ---------------- chart (any listed company) ----------------
    p0 = c.px_at(as_of)
    f['px0'] = rnd(p0)
    mc = c.mcap(as_of)[0]
    f['mcap_cr'] = rnd(mc, 1)
    f['size_band'] = None if mc is None else '<50' if mc < 50 else '50-500' if mc < 500 else '500-2k' if mc < 2000 \
        else '2k-10k' if mc < 10000 else '10k+'
    e0, s0 = c.eps.lookup(as_of), c.sales.lookup(as_of)
    f['eps_ttm'], f['sales_ttm'] = rnd(e0, 2), rnd(s0, 2)
    f['loss_ttm'] = None if e0 is None else int(e0 <= 0)

    def g1(ser, d):
        a, b = ser.lookup(d), ser.lookup(add_years(d, -1))
        return (a / b - 1) * 100 if a is not None and b is not None and b > 0 else None
    for nm, ser in (('eps', c.eps), ('sales', c.sales)):
        now = ser.lookup(as_of)
        f[f'{nm}_g1'] = rnd(g1(ser, as_of), 1)
        f[f'{nm}_g3'] = rnd(cagr(now, ser.lookup(add_years(as_of, -3)), 3), 1)
        f[f'{nm}_g5'] = rnd(cagr(now, ser.lookup(add_years(as_of, -5)), 5), 1)
        prev = g1(ser, add_years(as_of, -1))
        f[f'{nm}_g1_prev'] = rnd(prev, 1)
        f[f'{nm}_acc'] = rnd(f[f'{nm}_g1'] - prev, 1) if f[f'{nm}_g1'] is not None and prev is not None else None
        q1 = g1(ser, as_of - dt.timedelta(days=91))
        q2 = g1(ser, as_of - dt.timedelta(days=182))
        f[f'{nm}_g1_3m_ago'] = rnd(q1, 1)
        f[f'{nm}_g1_rising2q'] = None if None in (f[f'{nm}_g1'], q1, q2) else int(f[f'{nm}_g1'] > q1 > q2)
    pe = p0 / e0 if p0 and e0 and e0 > 0 else None
    f['pe'] = rnd(pe, 1)
    k = bisect.bisect_right(c.pxd, as_of)
    lo = bisect.bisect_right(c.pxd, add_years(as_of, -5))
    w = sorted(v for v in c.pe_w[lo:k] if v is not None)
    med = w[len(w) // 2] if len(w) >= 156 else None  # at least 3 of the 5 years with a positive P/E
    f['pe_med5'], f['pe_med5_wks'] = rnd(med, 1), len(w)
    f['pe_rel5'] = rnd(ratio(pe, med), 2)
    f['peg3'] = rnd(pe / f['eps_g3'], 3) if pe and f['eps_g3'] and f['eps_g3'] > 0 else None
    f['peg1'] = rnd(pe / f['eps_g1'], 3) if pe and f['eps_g1'] and f['eps_g1'] > 0 else None
    f['ps'] = rnd(ratio(mc, s0), 2) if s0 and s0 > 0 else None
    for nm, back in (('px_ret1', 365), ('px_ret6m', 182), ('px_ret3', 1095)):
        pb = c.px_at(as_of - dt.timedelta(days=back))
        f[nm] = rnd(p0 / pb, 3) if p0 and pb else None
    yr = [v for t, v in c.px[bisect.bisect_right(c.pxd, as_of - dt.timedelta(days=365)):k]]
    f['px_off_hi52'] = rnd(p0 / max(yr) - 1, 3) if p0 and yr else None
    sh0 = c.shares(as_of)
    for n in (1, 3):
        shn = c.shares(add_years(as_of, -n))
        f[f'shares_chg{n}'] = rnd((sh0 / shn - 1) * 100, 1) if sh0 and shn else None
    vd = [t for t, _ in c.vol]
    kv = bisect.bisect_right(vd, as_of)
    tv = [v * (c.px_at(t, 7) or 0) / 1e7 for t, v in c.vol[max(0, kv - 13):kv] if (as_of - t).days <= 100]
    f['tv13_med_cr'] = rnd(statistics.median(tv), 3) if len(tv) >= 8 else None
    src['chart'] = c.chart_basis
    if chart_only:
        return f, src

    # ---------------- annual statements ----------------
    b, ends = c.basis('profit_loss', as_of)
    pl = c.st['profit_loss'][b] if b else None
    src['stmt'], src['fy'] = b, ends[0].strftime('%b %Y') if ends else ''
    lender = bool(pl and any('Financing Profit' in col for col in pl.cols.values()))
    f['lender'] = int(lender) if pl else None
    ys = yearly(ends, pl.months if pl else {}, 5)
    P = lambda i, *lb: pl.get(ys[i], *lb) if pl and i < len(ys) else None
    f['fy_age_days'] = (as_of - ys[0]).days if ys else None
    sales = lambda i: P(i, 'Sales', 'Revenue')
    for nm, fn in (('sales', sales), ('np', lambda i: P(i, 'Net Profit')), ('eps', lambda i: P(i, 'EPS in Rs'))):
        f[f'fy_{nm}_g1'] = rnd(cagr(fn(0), fn(1), 1), 1)
        f[f'fy_{nm}_g3'] = rnd(cagr(fn(0), fn(3), 3), 1)
    f['opm'] = P(0, 'OPM %', 'Financing Margin %')
    o3 = [P(i, 'OPM %', 'Financing Margin %') for i in range(1, 4)]
    f['opm_chg3'] = rnd(f['opm'] - o3[2], 1) if f['opm'] is not None and o3[2] is not None else None
    f['opm_vs_avg3'] = rnd(f['opm'] - sum(o3) / 3, 1) if f['opm'] is not None and None not in o3 else None
    f['payout'] = P(0, 'Dividend Payout %')
    pbt, intr, oi = P(0, 'Profit before tax'), P(0, 'Interest'), P(0, 'Other Income')
    f['oi_share_pbt'] = rnd(ratio(oi, pbt), 2) if pbt and pbt > 0 else None
    f['tax_pct'] = P(0, 'Tax %')
    if not lender:
        f['int_cover'] = rnd((pbt + intr) / intr, 1) if pbt is not None and intr else (999 if intr == 0 and pbt and pbt > 0 else None)
    # balance sheet: the same basis, the latest balance filed (year-end or half-year)
    bs = c.st['balance_sheet'][b] if b else None
    bends = sorted((e for e in (bs.cols if bs else {}) if e + dt.timedelta(days=c.avail_lag('balance_sheet', e, 12)) <= as_of
                    and bs.get(e, 'Total Assets') is not None), reverse=True)
    B = lambda e, *lb: bs.get(e, *lb) if bs and e else None
    eq = lambda e: B(e, 'Equity Capital') + B(e, 'Reserves') if B(e, 'Equity Capital') is not None and \
        B(e, 'Reserves') is not None else None
    debt = lambda e: B(e, 'Borrowings', 'Borrowing')
    bl = bends[0] if bends else None
    src['bs'] = bl.strftime('%b %Y') if bl else ''
    # lenders: borrowing is the business, so debt, interest-cover, ROCE and cash-conversion tests don't apply (rule 4)
    f['de'] = rnd(debt(bl) / eq(bl), 2) if not lender and bl and debt(bl) is not None and eq(bl) and eq(bl) > 0 else None
    f['eq_cap_chg3'] = None
    fyb = [e for e in bends if e.month == c.fy_month]  # year-end balances
    opn = lambda e: next((x for x in fyb if 330 <= (e - x).days <= 400), None)  # the balance a year earlier

    def roe(i):
        if i >= len(ys) or ys[i] not in fyb:
            return None
        e0_, e1_ = eq(ys[i]), eq(opn(ys[i]))
        npf = P(i, 'Net Profit')
        return npf / ((e0_ + e1_) / 2) * 100 if npf is not None and e0_ and e1_ and e0_ + e1_ > 0 else None
    f['roe'] = rnd(roe(0), 1)
    r3 = [roe(i) for i in range(3)]
    f['roe_avg3'] = rnd(sum(r3) / 3, 1) if None not in r3 else None
    if ys and ys[0] in fyb:
        e3 = next((x for x in fyb if 1060 <= (ys[0] - x).days <= 1130), None)
        if e3 and B(ys[0], 'Equity Capital') and B(e3, 'Equity Capital'):
            f['eq_cap_chg3'] = rnd((B(ys[0], 'Equity Capital') / B(e3, 'Equity Capital') - 1) * 100, 1)
    if lender:
        ta = lambda e: B(e, 'Total Assets')
        f['roa'] = rnd(P(0, 'Net Profit') / ((ta(ys[0]) + ta(opn(ys[0]))) / 2) * 100, 2) \
            if ys and ys[0] in fyb and opn(ys[0]) and P(0, 'Net Profit') is not None and ta(ys[0]) and ta(opn(ys[0])) else None
    else:
        op = P(0, 'Operating Profit')
        f['debt_ebitda'] = rnd(debt(bl) / op, 2) if bl and debt(bl) is not None and op and op > 0 else None
    # ratios table (same basis): ROCE and working-capital days as screener computes them
    rt = c.st['ratios'][b] if b else None
    R = lambda i, lb: rt.get(ys[i], lb) if rt and i < len(ys) else None
    if not lender:
        f['roce'] = R(0, 'ROCE %')
        rc = [R(i, 'ROCE %') for i in range(3)]
        f['roce_avg3'] = rnd(sum(rc) / 3, 1) if None not in rc else None
        f['roce_min3'] = min(rc) if None not in rc else None
        f['debtor_days'], f['wc_days'], f['ccc_days'] = R(0, 'Debtor Days'), R(0, 'Working Capital Days'), \
            R(0, 'Cash Conversion Cycle')
    # cash flow (same basis; older years count only from the annual report)
    cf = c.st['cash_flow'][b] if b else None
    cfy = [e for e in ys if cf and cf.get(e, 'Cash from Operating Activity') is not None
           and e + dt.timedelta(days=c.avail_lag('cash_flow', e, 12)) <= as_of]
    for n in (2, 3, 5):
        yy = cfy[:n]  # the newest n years with a filed cash flow, consecutive in the P&L chain
        if not lender and len(yy) == n and yy == ys[ys.index(yy[0]):ys.index(yy[0]) + n]:
            cfo = sum(cf.get(e, 'Cash from Operating Activity') for e in yy)
            npl = [pl.get(e, 'Net Profit') for e in yy]
            f[f'cfo_pat_{n}y'] = rnd(cfo / sum(npl), 2) if None not in npl and sum(npl) > 0 else None
        else:
            f[f'cfo_pat_{n}y'] = None
    src['cf'] = cfy[0].strftime('%b %Y') if cfy else ''
    # Piotroski-style score from what screener gives (8 of the 9 tests; no current ratio): needs two years of P&L,
    # balance sheet and cash flow
    f['fscore8'] = None
    if not lender and len(ys) >= 2 and ys[0] in fyb and ys[1] in fyb and cfy[:1] == ys[:1]:
        ta0, ta1 = B(ys[0], 'Total Assets'), B(ys[1], 'Total Assets')
        n0, n1 = P(0, 'Net Profit'), P(1, 'Net Profit')
        cfo0 = cf.get(ys[0], 'Cash from Operating Activity')
        vals = [ta0, ta1, n0, n1, cfo0, debt(ys[0]), debt(ys[1]), sales(0), sales(1), P(0, 'OPM %'), P(1, 'OPM %')]
        if None not in vals and ta0 > 0 and ta1 > 0:
            tests = [n0 > 0, cfo0 > 0, n0 / ta0 > n1 / ta1, cfo0 > n0, debt(ys[0]) / ta0 <= debt(ys[1]) / ta1,
                     f['shares_chg1'] <= 2 if f['shares_chg1'] is not None else None,  # no new shares (2% rounding room)
                     P(0, 'OPM %') > P(1, 'OPM %'), sales(0) / ta0 > sales(1) / ta1]
            f['fscore8'] = sum(1 for t in tests if t) if None not in tests else None
    # restatement / basis check: statement sales against the chart's TTM sales after that year's results
    gaps = []
    for e in ys[:4]:
        sv = sales(ys.index(e))
        cv = c.sales.lookup(e + dt.timedelta(days=75)) if c.sales.raw else None
        if sv and cv and abs(sv - cv) / abs(cv) > 0.10:
            gaps.append(e.strftime('%b%Y'))
    f['stmt_gap_fy'] = ' '.join(gaps) if gaps else None

    # ---------------- quarterly (13 quarters) ----------------
    qb, qends = c.basis('quarterly', as_of)
    qt = c.st['quarterly'][qb] if qb else None
    src['q'] = qends[0].strftime('%b %Y') if qends else ''
    Q = lambda e, *lb: qt.get(e, *lb) if qt and e else None
    back = lambda e, n: next((x for x in qends if abs((e - x).days - 91 * n) <= 20), None)

    def yoy(e, *lb):
        a, p = Q(e, *lb), Q(back(e, 4), *lb)
        return (a / p - 1) * 100 if a is not None and p is not None and p > 0 else None
    q0 = qends[0] if qends else None
    qs = [q0, back(q0, 1) if q0 else None, back(q0, 2) if q0 else None]
    for nm, lb in (('sales', ('Sales', 'Revenue')), ('eps', ('EPS in Rs',)), ('np', ('Net Profit',))):
        v = [yoy(e, *lb) if e else None for e in qs]
        f[f'q_{nm}_yoy'] = rnd(v[0], 1)
        f[f'q_{nm}_yoy_rising2q'] = None if None in v else int(v[0] > v[1] > v[2])
    f['q_accel'] = None if f['q_eps_yoy'] is None or f['q_sales_yoy'] is None or f['q_eps_yoy_rising2q'] is None \
        else int(f['q_eps_yoy'] >= 25 and f['q_sales_yoy'] >= 20 and f['q_eps_yoy_rising2q'] == 1)
    f['q_opm'] = Q(q0, 'OPM %', 'Financing Margin %')
    po = Q(back(q0, 4), 'OPM %', 'Financing Margin %') if q0 else None
    f['q_opm_yoy_chg'] = rnd(f['q_opm'] - po, 1) if f['q_opm'] is not None and po is not None else None
    s_ = [Q(e, 'Sales', 'Revenue') for e in qs]
    o_ = [Q(e, 'OPM %', 'Financing Margin %') for e in qs]
    f['q_sales_opm_fall2q'] = None if None in s_ + o_ else int(s_[0] < s_[1] < s_[2] and o_[0] < o_[1] < o_[2])
    f['gnpa'], f['nnpa'] = Q(q0, 'Gross NPA %'), Q(q0, 'Net NPA %')

    # ---------------- shareholding ----------------
    filed = sorted((e for e, v in c.shp.items() if v.get('filed') and v['filed'] <= as_of), reverse=True)
    S = lambda e, k: c.shp[e].get(k) if e in c.shp else None
    s0q = filed[0] if filed else None
    src['shp'] = s0q.strftime('%b %Y') if s0q else ''
    if s0q and (as_of - s0q).days > 200:
        s0q = None  # stale: the window starts before the saved quarters
    sb = lambda n: next((x for x in filed if abs((s0q - x).days - 91 * n) <= 20), None) if s0q else None
    f['prom_pct'] = S(s0q, 'prom')
    for nm, n in (('1y', 4), ('3y', 12)):
        a, p = S(s0q, 'prom'), S(sb(n), 'prom')
        f[f'prom_chg_{nm}'] = rnd(a - p, 2) if a is not None and p is not None else None
    f['pledge_pct'] = S(s0q, 'pledge')
    pl4 = [S(x, 'pledge') for x in (s0q, sb(1), sb(2), sb(3))]
    f['pledge_new_4q'] = None if None in pl4 else int(any(pl4[i] > pl4[i + 1] + 0.01 for i in range(3)))
    f['inst_pct'] = rnd(S(s0q, 'inst'), 2) if S(s0q, 'inst') is not None else None
    a, p = S(s0q, 'inst'), S(sb(4), 'inst')
    f['inst_chg_1y'] = rnd(a - p, 2) if a is not None and p is not None else None
    used = [x for x in (s0q, sb(1), sb(2), sb(3), sb(4), sb(12)) if x]
    src['shp_via'] = '+'.join(sorted({p for x in used for p in (c.shp[x].get('src') or '').split('+') if p}))
    return f, src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows')
    ap.add_argument('--candidates', action='store_true')
    ap.add_argument('--market', action='store_true')
    ap.add_argument('--from', dest='frm', default='2006')
    ap.add_argument('--chart-only', action='store_true')
    ap.add_argument('--syms')
    ap.add_argument('--out')
    ap.add_argument('--companies', default=os.path.join('data', 'companies'))
    a = ap.parse_args()
    D = hist_dir()
    if a.market:
        src_file = os.path.join(D, 'outcomes.csv')
    else:
        src_file = a.rows or os.path.join(D, 'sample_candidates.csv' if a.candidates else 'sample.csv')
    rows = list(csv.DictReader(open(src_file, encoding='utf-8')))
    for r in rows:
        r['as_of'] = r.get('as_of') or r.get('start')
    rows = [r for r in rows if r['as_of'] and r['as_of'][:4] >= (a.frm if a.market else '0')]
    if a.syms:
        keep = set(a.syms.split(','))
        rows = [r for r in rows if r['sym'] in keep]
    if a.market:  # only what identifies the row; outcomes stay in outcomes.csv
        rows = [{'sym': r['sym'], 'as_of': r['as_of']} for r in rows]
    bt = {}
    btf = os.path.join(D, 'business_types.csv')
    if os.path.exists(btf):
        for r in csv.DictReader(open(btf, encoding='utf-8')):
            bt.setdefault(r['sym'], {})[r['as_of']] = r
    t0, out, bysym = time.time(), [], {}
    for r in rows:
        bysym.setdefault(r['sym'], []).append(r)
    for n, (sym, rs) in enumerate(sorted(bysym.items())):
        c = Company(sym, a.companies, a.chart_only)
        for r in rs:
            f, src = features(c, dt.date.fromisoformat(r['as_of'][:10]), a.chart_only)
            o = {'sym': sym, 'as_of': r['as_of'][:10]}
            for k in ('group', 'horizon', 'matched_to', 'mc0'):
                if k in r:
                    o[k] = r[k]
            t = (bt.get(sym) or {}).get(o['as_of'])
            if t is None and bt.get(sym):  # typed at another window start of the same company
                k = min(bt[sym], key=lambda x: abs((dt.date.fromisoformat(x) - dt.date.fromisoformat(o['as_of'])).days))
                t, o['bt_as_of'] = bt[sym][k], k
            for k in ('business_type', 'sub_type', 'cyclicality', 'capital_intensity', 'pricing_power', 'customers'):
                o[k] = (t or {}).get(k) or None
            o.update(f)
            o.update({f'src_{k}': v or None for k, v in src.items()})
            o['source'] = '; '.join(f'{k}:{v}' for k, v in src.items() if v) or None
            out.append(o)
        if n and n % 500 == 0:
            print(f'{n} companies, {len(out)} rows, {time.time() - t0:.0f}s', flush=True)
    keys = []
    for o in out:
        keys += [k for k in o if k not in keys]
    path = a.out or os.path.join(D, 'features.csv')
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    # coverage: share of rows with each feature, by start period
    bands = [('2006-08', '2006', '2008'), ('2009-11', '2009', '2011'), ('2012-14', '2012', '2014'),
             ('2015-17', '2015', '2017'), ('2018-20', '2018', '2020'), ('2021-23', '2021', '2023'), ('2024+', '2024', '9999')]
    grp = {b[0]: [o for o in out if b[1] <= o['as_of'][:4] <= b[2]] for b in bands}
    grp = {k: v for k, v in grp.items() if v}
    skip = {'sym', 'as_of', 'group', 'horizon', 'matched_to', 'mc0', 'source', 'bt_as_of'}
    lines = [f'# Feature coverage ({os.path.basename(path)}, {len(out)} rows, {len(bysym)} companies, '
             f'{time.time() - t0:.0f}s)', '',
             'Share of rows with a value (missing stays empty, never 0), by window start. `src_*` columns: the basis or '
             'latest period used.', '',
             '| feature | ' + ' | '.join(f'{k} (n={len(v)})' for k, v in grp.items()) + ' | all |',
             '|---|' + '---|' * (len(grp) + 1)]
    for k in keys:
        if k in skip:
            continue
        cells = [f'{100 * sum(1 for o in v if o.get(k) not in (None, "")) / len(v):.0f}%' for v in grp.values()]
        allp = 100 * sum(1 for o in out if o.get(k) not in (None, '')) / len(out) if out else 0
        lines.append(f'| {k} | ' + ' | '.join(cells) + f' | {allp:.0f}% |')
    cov = os.path.splitext(path)[0] + '_coverage.md'
    open(cov, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'{len(out)} rows, {len(bysym)} companies, {time.time() - t0:.0f}s -> {path}, {cov}')


if __name__ == '__main__':
    main()
