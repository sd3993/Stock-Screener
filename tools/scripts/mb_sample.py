import csv, os, random, sys
# Multibagger study, step 2 (process/historical/s2_sample.md): picks winners, fallen winners and ~5 control candidates per
# winner from outcomes.csv (S1), seeded so the picks repeat. Writes runs/historical/<date>/sample_candidates.csv (group, sym,
# horizon, start, mc0, multiples, reason, matched_to) and prints counts per group, horizon, period and size band.
# The control for each winner is chosen from its candidates after business types are tagged (S2 helper).
#   python -I tools/scripts/mb_sample.py [--seed 1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir
a = sys.argv[1:]
SEED = int(a[a.index('--seed') + 1]) if '--seed' in a else 1
D = hist_dir()
# horizon: (multiple columns tried in order, threshold, last window start, winners to pick)
H = {'short': (['px_2y'], 2, '2023-12-31', 70), 'medium': (['px_5y'], 3, '2021-12-31', 80),
     'long': (['px_7y', 'px_10y'], 10, '2019-12-31', 50)}
FALLEN = 50  # per horizon short and medium
N_CAND = 5
MIN_MC = 50

def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

rows = [r for r in csv.DictReader(open(os.path.join(D, 'outcomes.csv'), encoding='utf-8'))]
for r in rows:
    for k, v in r.items():
        if k not in ('sym', 'start', 'last_price_date'):
            r[k] = f(v)
rows = [r for r in rows if r['mc0'] and r['mc0'] >= MIN_MC and '2006' <= r['start'][:4] <= '2023']
by_start = {}
for r in rows:
    by_start.setdefault(r['start'], []).append(r)

def mult(r, cols):
    vals = [r.get(c) for c in cols if r.get(c) is not None]
    return max(vals) if vals else None

def band(mc):
    return '50-500' if mc < 500 else '500-2k' if mc < 2000 else '2k-10k' if mc < 10000 else '10k+'

def period(s):
    return 'discovery' if s[:4] <= '2015' else 'test'

def dilution_note(r, n):
    px, mc = r.get(f'px_{n}y'), r.get(f'mc_{n}y')
    if px and mc and not (0.67 <= mc / px <= 1.5):
        return f'; mc multiple {mc:.1f}x vs price {px:.1f}x ({"dilution" if mc > px else "buyback/shrink"})'
    return ''

def pick_strat(pool, n, rng):
    """n picks spread evenly over period x size band cells (leftover slots go to the largest cells)."""
    cells = {}
    for r in pool:
        cells.setdefault((period(r['start']), band(r['mc0'])), []).append(r)
    for c in cells.values():
        rng.shuffle(c)
    out = []
    while len(out) < n and any(cells.values()):
        for k in sorted(cells):
            if cells[k] and len(out) < n:
                out.append(cells[k].pop())
    return out

rng = random.Random(SEED)
out = []
for hz, (cols, thr, last, n) in H.items():
    yrs = cols[0].split('_')[1][:-1]
    first = {}  # each company's first qualifying window for this horizon
    for r in sorted(rows, key=lambda r: r['start']):
        m = mult(r, cols)
        if r['start'] <= last and m is not None and m >= thr and r['sym'] not in first:
            first[r['sym']] = r
    winners = pick_strat(list(first.values()), n, rng)
    for w in winners:
        m = mult(w, cols)
        strong = hz == 'medium' and m >= 5
        out.append({'group': 'winner', 'sym': w['sym'], 'horizon': hz, 'start': w['start'], 'mc0': w['mc0'],
                    'multiple': m, 'strong': 'yes' if strong else '', 'matched_to': '',
                    'reason': f'{hz}: {m:.1f}x price over {"7-10" if hz == "long" else yrs} years from {w["start"]}{dilution_note(w, yrs)}'})
        # control candidates: same start, mc0 within 0.5-2x, did not reach the threshold; nearest on growth and valuation
        cands = []
        for c in by_start[w['start']]:
            cm = mult(c, cols)
            if c['sym'] == w['sym'] or cm is None or cm >= thr or not (0.5 <= c['mc0'] / w['mc0'] <= 2):
                continue
            dist = abs((c['sales_g3'] or 0) - (w['sales_g3'] or 0)) / 20 + abs((c['eps_g3'] or 0) - (w['eps_g3'] or 0)) / 40 \
                + abs((c['pe0'] or 0) - (w['pe0'] or 0)) / 20 + abs(c['mc0'] / w['mc0'] - 1)
            cands.append((dist, c, cm))
        for dist, c, cm in sorted(cands, key=lambda x: x[0])[:N_CAND]:
            out.append({'group': 'control_candidate', 'sym': c['sym'], 'horizon': hz, 'start': c['start'], 'mc0': c['mc0'],
                        'multiple': cm, 'strong': '', 'matched_to': w['sym'],
                        'reason': f'looked like {w["sym"]} at {c["start"]} (distance {dist:.2f}); reached {cm:.1f}x'})
    if hz in ('short', 'medium'):
        fallen = {}
        for r in sorted(rows, key=lambda r: r['start']):
            pk, end = r.get(f'pxpeak_{yrs}y'), r.get(f'px_{yrs}y')
            if r['start'] <= last and pk and end and pk >= thr and end <= pk / 2 and r['sym'] not in fallen:
                fallen[r['sym']] = r
        for r in pick_strat(list(fallen.values()), FALLEN, rng):
            out.append({'group': 'fallen_winner', 'sym': r['sym'], 'horizon': hz, 'start': r['start'], 'mc0': r['mc0'],
                        'multiple': r[f'px_{yrs}y'], 'strong': '', 'matched_to': '',
                        'reason': f'{hz}: peaked at {r[f"pxpeak_{yrs}y"]:.1f}x within {yrs} years from {r["start"]}, ended at {r[f"px_{yrs}y"]:.1f}x'})
    print(f'{hz}: pool {len(first)} winners')

keys = ['group', 'sym', 'horizon', 'start', 'mc0', 'multiple', 'strong', 'matched_to', 'reason']
with open(os.path.join(D, 'sample_candidates.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(out)
cnt = {}
for r in out:
    k = (r['group'], r['horizon'], period(r['start']), band(r['mc0']))
    cnt[k] = cnt.get(k, 0) + 1
for k in sorted(cnt):
    print(*k, cnt[k])
print('rows', len(out), '| distinct companies', len({r['sym'] for r in out}),
      '| winners without candidates:', [r['sym'] for r in out if r['group'] == 'winner'
                                        and not any(c['matched_to'] == r['sym'] and c['horizon'] == r['horizon'] for c in out)])
