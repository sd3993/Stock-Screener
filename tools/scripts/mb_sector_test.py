# Sector premise test (scripts only): are multibaggers concentrated by industry beyond chance, does a company's own growth
# pay without its industry growing, and did anything visible at the start predict which industries produced winners?
# Reads outcomes.csv (S6, process/s6_playbook.md) and screener's industry labels (scr/overview.json `sectors`); writes sector_test.md in the run
# folder. Usage: python -I tools/scripts/mb_sector_test.py [--months 03] [--level industry|sector] [--out FILE]
# Caveats printed with the results: labels are today's classification; the universe is mostly companies still listed.
import argparse, csv, json, os, random, statistics as st, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.environ.get('PLAYBOOK_DATA') or os.path.join(ROOT, 'data', 'playbook')  # the playbook base data folder (config.playbook_dir)
COMPANIES = os.path.join(ROOT, 'data', 'companies')
H = {'short': (2, 2.0, ['2y']), 'medium': (5, 3.0, ['5y']), 'long': (7, 10.0, ['7y', '10y'])}  # years, multiple, windows
FLOOR, MIN_N, SHUFFLES = 50.0, 5, 300

def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

_lab = {}
def label(sym):
    if sym not in _lab:
        s = None
        try:
            s = [x for x in json.load(open(os.path.join(COMPANIES, sym, 'scr', 'overview.json'), encoding='utf-8'))['data'].get('sectors') or [] if x]
        except (OSError, ValueError, KeyError, AttributeError, TypeError):
            pass
        _lab[sym] = (s[0], s[-1]) if s else None
    return _lab[sym]

def winner(r, hz):
    """True/False, or None when no window of the horizon has ended. The market-cap multiple must reach half the
    threshold when it is known (guards against unadjusted splits)."""
    _, thr, wins = H[hz]
    seen = None
    for w in wins:
        px, mc = f(r['px_' + w]), f(r['mc_' + w])
        if px is None:
            continue
        seen = seen or False
        if px >= thr and (mc is None or mc >= thr / 2):
            seen = True
    return seen

def plus_years(d, n):
    return f'{int(d[:4]) + n}{d[4:]}'

def tercile(vals):
    s = sorted(vals)
    return s[len(s) // 3], s[2 * len(s) // 3]

def spearman(a, b):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rk(a), rk(b); ma, mb = st.mean(ra), st.mean(rb)
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / den if den else None

def top_share(groups, q=0.2):
    """Groups ranked by winner rate; the top ones holding ~q of companies: (their share of winners, their winner rate)."""
    tot_n = sum(n for n, _ in groups); tot_w = sum(w for _, w in groups)
    n = w = 0
    for gn, gw in sorted(groups, key=lambda g: -g[1] / g[0]):
        take = min(gn, q * tot_n - n)
        if take <= 0:
            break
        n += take; w += gw * take / gn
    return (w / tot_w if tot_w else 0), (w / n if n else 0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--months', default='03'); ap.add_argument('--level', default='industry', choices=['industry', 'sector'])
    ap.add_argument('--out', default=os.path.join(D, 'sector_test.md'))
    a = ap.parse_args()
    months = set(a.months.split(',')); li = 1 if a.level == 'industry' else 0
    random.seed(1)
    rows = list(csv.DictReader(open(os.path.join(D, 'outcomes.csv'), encoding='utf-8')))
    by_key = {(r['sym'], r['start']): r for r in rows}
    out = [f'# Sector premise test ({a.level} labels, starts in month {a.months}, start market cap >= {FLOOR:.0f} cr, groups of {MIN_N}+)', '']
    for hz, (yrs, thr, wins) in H.items():
        dates = defaultdict(list)
        for r in rows:
            if r['start'][5:7] not in months or (f(r['mc0']) or 0) < FLOOR:
                continue
            w = winner(r, hz); lab = label(r['sym'])
            if w is None or not lab:
                continue
            dates[r['start']].append((r, lab[li], w))
        out += [f'## {hz}: {thr:g}x in {"/".join(wins)}', '']
        # A. concentration against shuffled labels
        out += ['### A. Concentration', '', '| start | companies | industries | base rate | top-20% industries: winner rate | their share of winners | by chance | z |', '|---|---|---|---|---|---|---|---|']
        pooled = []; grid = defaultdict(lambda: [0, 0]); grid2 = defaultdict(lambda: [0, 0]); feats = defaultdict(list); lifts = defaultdict(lambda: [0, 0, 0, 0])
        for d in sorted(dates):
            g = defaultdict(list)
            for r, lab, w in dates[d]:
                g[lab].append((r, w))
            g = {k: v for k, v in g.items() if len(v) >= MIN_N}
            items = [(r, k, w) for k, v in g.items() for r, w in v]
            nw = sum(w for _, _, w in items)
            if len(g) < 10 or nw < 10:
                continue
            base = nw / len(items)
            act, rate = top_share([(len(v), sum(w for _, w in v)) for v in g.values()])
            labs = [k for _, k, _ in items]; ws = [w for _, _, w in items]; sh = []
            for _ in range(SHUFFLES):
                random.shuffle(ws); gg = defaultdict(lambda: [0, 0])
                for k, w in zip(labs, ws):
                    gg[k][0] += 1; gg[k][1] += w
                sh.append(top_share([tuple(v) for v in gg.values()])[0])
            mu, sd = st.mean(sh), st.pstdev(sh)
            z = (act - mu) / sd if sd else 0
            pooled.append((d, base, act, mu, z, rate))
            out.append(f'| {d} | {len(items)} | {len(g)} | {base:.1%} | {rate:.1%} | {act:.0%} | {mu:.0%} | {z:.1f} |')
            # B. own growth x industry growth (leave one out), over the window
            end = plus_years(d, yrs); own = {}
            for r, k, w in items:
                e = by_key.get((r['sym'], end))
                if not e:
                    continue
                s0, s1, e0, e1 = f(r['sales0']), f(e['sales0']), f(r['eps0']), f(e['eps0'])
                own[r['sym']] = (s1 / s0 if s0 and s1 and s0 > 0 else None, e1 / e0 if e0 and e1 and e0 > 0 and e1 > 0 else None, k, w, f(r['px_' + wins[0]]))
            ind_s = defaultdict(list); ind_p = defaultdict(list)
            for sym, (sg, eg, k, w, px) in own.items():
                if sg is not None:
                    ind_s[k].append((sym, sg))
                if px is not None:
                    ind_p[k].append((sym, px))
            def loo(lst, sym):
                v = [x for s, x in lst if s != sym]
                return st.median(v) if len(v) >= MIN_N - 1 else None
            cells = [(eg, loo(ind_s[k], sym), loo(ind_p[k], sym), w) for sym, (sg, eg, k, w, px) in own.items() if eg is not None]
            cells = [c for c in cells if c[1] is not None and c[2] is not None]
            if len(cells) >= 60:
                te, ts, tp = tercile([c[0] for c in cells]), tercile([c[1] for c in cells]), tercile([c[2] for c in cells])
                b = lambda v, t: 0 if v < t[0] else 1 if v < t[1] else 2
                for eg, sg, pg, w in cells:
                    grid[(b(eg, te), b(sg, ts))][0] += 1; grid[(b(eg, te), b(sg, ts))][1] += w
                    grid2[(b(eg, te), b(pg, tp))][0] += 1; grid2[(b(eg, te), b(pg, tp))][1] += w
            # C. what was visible at the start, per industry
            def med(v, key, fn=None):
                x = [f(r[key]) for r, _ in v]; x = [y for y in x if y is not None]
                return (fn(x) if fn else st.median(x)) if len(x) >= MIN_N - 1 else None
            def rel(v):
                x = [f(r['pe0']) / f(r['pe_med5']) for r, _ in v if f(r['pe0']) and f(r['pe_med5']) and f(r['pe0']) > 0]
                return st.median(x) if len(x) >= MIN_N - 1 else None
            F = {'sales growth 1y (median)': lambda v: med(v, 'sales_g1'), 'sales growth 3y (median)': lambda v: med(v, 'sales_g3'),
                 'EPS growth 1y (median)': lambda v: med(v, 'eps_g1'), 'EPS growth 3y (median)': lambda v: med(v, 'eps_g3'),
                 'price return 1y (median)': lambda v: med(v, 'px_ret1'),
                 'breadth: share up over 1y': lambda v: med(v, 'px_ret1', lambda x: sum(y > 0 for y in x) / len(x)),
                 'P/E (median)': lambda v: med(v, 'pe0'), 'P/E vs own 5y median': rel,
                 'sales growth accel (1y - 3y)': lambda v: (lambda x, y: x - y if x is not None and y is not None else None)(med(v, 'sales_g1'), med(v, 'sales_g3'))}
            for name, fn in F.items():
                xs = [(fn(v), sum(w for _, w in v) / len(v), len(v), sum(w for _, w in v)) for v in g.values()]
                xs = [x for x in xs if x[0] is not None]
                if len(xs) < 10:
                    continue
                feats[name].append((d, spearman([x[0] for x in xs], [x[1] for x in xs])))
                srt = sorted(xs, key=lambda x: x[0]); q = max(1, len(srt) // 5)
                per = 'disc' if d < '2016' else 'test'
                for tag, part in (('hi', srt[-q:]), ('lo', srt[:q])):
                    L = lifts[(name, per, tag)]; L[0] += sum(x[2] for x in part); L[1] += sum(x[3] for x in part)
                L = lifts[(name, per, 'all')]; L[0] += sum(x[2] for x in xs); L[1] += sum(x[3] for x in xs)
        if pooled:
            out += ['', f'Mean over {len(pooled)} start dates: top-20% industries held {st.mean(p[2] for p in pooled):.0%} of winners against {st.mean(p[3] for p in pooled):.0%} by chance (mean z {st.mean(p[4] for p in pooled):.1f}); their winner rate {st.mean(p[5] for p in pooled):.1%} against a base rate of {st.mean(p[1] for p in pooled):.1%}.', '']
        for title, G, col in (('B1. Winner rate: own EPS growth over the window (rows) x industry sales growth over the window, leave one out (columns)', grid, 'industry sales growth'),
                              ('B2. Same rows x industry median price multiple over the window, leave one out (columns)', grid2, 'industry price multiple')):
            out += [f'### {title}', '', f'| own EPS growth | {col}: low | mid | high |', '|---|---|---|---|']
            for i, nm in enumerate(('low', 'mid', 'high')):
                out.append(f'| {nm} | ' + ' | '.join(f'{G[(i, j)][1] / G[(i, j)][0]:.1%} ({G[(i, j)][0]})' if G[(i, j)][0] else '-' for j in range(3)) + ' |')
            out.append('')
        out += ['### C. Visible at the start: industry feature against the industry\'s later winner rate', '',
                '| feature | mean rank corr 2006-15 | dates positive | mean rank corr 2016+ | dates positive | lift top-20% industries 2006-15 | 2016+ | lift bottom-20% 2006-15 | 2016+ |', '|---|---|---|---|---|---|---|---|---|']
        for name, v in feats.items():
            cell = []
            for per, sel in (('disc', lambda d: d < '2016'), ('test', lambda d: d >= '2016')):
                c = [x for d, x in v if sel(d) and x is not None]
                cell += [f'{st.mean(c):+.2f}' if c else '-', f'{sum(x > 0 for x in c)}/{len(c)}' if c else '-']
            def lift(per, tag):
                L, A = lifts[(name, per, tag)], lifts[(name, per, 'all')]
                return f'{(L[1] / L[0]) / (A[1] / A[0]):.2f}' if L[0] and A[1] else '-'
            out.append(f'| {name} | ' + ' | '.join(cell) + f' | {lift("disc", "hi")} | {lift("test", "hi")} | {lift("disc", "lo")} | {lift("test", "lo")} |')
        out.append('')
    out += ['## Caveats', '- Labels are today\'s NSE classification (screener\'s copy), not the one at the start date.',
            '- The universe is mostly companies still listed, so winner rates are overstated.',
            '- Windows from yearly starts overlap, so the dates are not independent.',
            '- B uses growth over the window (known only afterwards): it tests the premise, it is not a usable signal.']
    open(a.out, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    sys.stdout.reconfigure(encoding='utf-8'); print('\n'.join(out))

if __name__ == '__main__':
    main()
