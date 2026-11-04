import csv, os, random, sys
# Multibagger study, step 2 (process/historical/s2_sample.md): picks winners, fallen winners and ~5 control candidates per
# winner from outcomes.csv (S1), seeded so the picks repeat. Writes runs/historical/<date>/sample_candidates.csv (group, sym,
# horizon, start, mc0, multiples, reason, matched_to) and prints counts per group, horizon, period and size band.
# --finalize (after each business-type tagging round): merges the batch files, picks each winner's control (nearest candidate
# of the same type), counts the peers flags and runs the checks; outputs and rules in s2_sample.md, "Script".
# Candidates come from the winner's basic industry (screener's NSE label), then its sector; --coverage reports how many
# winners get the full count with the labels saved so far.
#   python -I tools/scripts/mb_sample.py [--seed 1] [--repair <old sample_candidates.csv> [--candidates-only]] | --coverage
#     | --finalize  [--companies <dir>] [--dir DIR: read and write there, not the run folder]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir
a = sys.argv[1:]
SEED = int(a[a.index('--seed') + 1]) if '--seed' in a else 1
D = a[a.index('--dir') + 1] if '--dir' in a else hist_dir()
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

# --- --finalize: once business types are tagged (s2_sample.md, "Checks") ---
COMPANIES = a[a.index('--companies') + 1] if '--companies' in a else os.path.join('data', 'companies')  # tests point it at a copy
# Artefact limits: a start mc under FLOOR_NEAR cr is near the floor, and thin if the median weekly traded value in the 13
# weeks before the start is under THIN_VALUE lakh or THIN_ZERO+ of those weeks had no volume (the chart's volume points are
# weekly totals); weekly price steps of STEP x are checked, and a market-cap-to-sales step off by more than MISMATCH x fails;
# gaps over GAP_BREAK days are breaks (over GAP_WARN, a warning); a start price older than STALE days is stale.
FLOOR_NEAR, THIN_VALUE, THIN_ZERO = 100, 5.0, 4
STEP, MISMATCH, GAP_BREAK, GAP_WARN, STALE = 1.5, 1.5, 90, 35, 14
BT_COLS = ['sym', 'as_of', 'business_type', 'sub_type', 'revenue_drivers', 'cyclicality', 'capital_intensity', 'pricing_power',
           'customers', 'evidence', 'peers', 'flag']
import bisect, datetime as dt, glob, json, re

def type_list():
    """Types from s2_sample.md's "Business type" list plus business_types/new_types*.md: [(name, definition, source)]."""
    txt = open(os.path.join('process', 'historical', 's2_sample.md'), encoding='utf-8').read()
    m = re.search(r'Keep the type list short and economic, e\.g\. (.*?); add a type', txt)
    out, depth, cur = [], 0, ''
    for ch in (m.group(1) if m else '') + ',':
        depth += (ch == '(') - (ch == ')')
        if ch == ',' and depth == 0:
            nm = cur.strip()
            base = nm.split(' (')[0] if nm.startswith('specialty manufacturer') else nm  # the bracket is its definition
            out.append((base, nm[len(base):].strip(' ()'), 's2_sample.md'))
            cur = ''
        else:
            cur += ch
    for fn in sorted(glob.glob(os.path.join(D, 'business_types', 'new_types*.md'))):
        for line in open(fn, encoding='utf-8'):
            m = re.match(r'\s*-\s*\*\*(.+?)\*\*\s*(\(.*?\))?\s*:\s*(.+)', line)
            if m and m.group(1).strip().lower() not in {t[0].lower() for t in out}:
                out.append((m.group(1).strip(), m.group(3).strip(), f'{os.path.basename(fn)} {m.group(2) or ""}'.strip()))
    return out

def norm_type(t, types):
    k = (t or '').strip().lower()
    for name, _, _ in types:
        if name.lower() in (k, k.split(' (')[0]):
            return name
    return None

_hist = {}
def history(sym):
    if sym not in _hist:
        fn = os.path.join(COMPANIES, sym, 'scr', 'history.json')
        h = json.load(open(fn, encoding='utf-8'))['data'] if os.path.exists(fn) else None
        def ser(key, name):
            out = []
            for p in ((h or {}).get(key) or {}).get('datasets', {}).get(name) or []:
                try:
                    out.append((dt.date.fromisoformat(p[0]), float(p[1])))
                except (TypeError, ValueError, IndexError):
                    pass
            return sorted(out)
        _hist[sym] = None if h is None else {'px': ser('price', 'Price'), 'vol': ser('price', 'Volume'),
                                              'mcs': ser('mcap_sales', 'Market Cap to Sales'), 'sales': ser('mcap_sales', 'Sales')}
    return _hist[sym]

def at(s, d, max_gap):
    i = bisect.bisect_right([x[0] for x in s], d) - 1
    return s[i][1] if i >= 0 and (d - s[i][0]).days <= max_gap else None

def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)

def artefacts(sym, start, n, mc0, o, group):
    """(fails, warnings) for one window. Screener's prices are adjusted for splits and bonuses, so a fail needs evidence:
    a split/bonus ex-date (NSE corporate actions, where saved) with a price step around it; a price step whose
    market-cap-to-sales step disagrees beyond that ratio's rounding to one decimal (only where TTM sales didn't change in
    between); a one-week spike that sets a fallen winner's peak; a step into the window end; a gap that hides a price step;
    a stale start price; thin trading near the floor. Steps that can't be verified, other gaps and a price multiple far
    above the market-cap multiple are warnings."""
    fails, warns = [], []
    h = history(sym)
    if not h or not h['px']:
        return fails, ['no history.json to check']
    st = dt.date.fromisoformat(start)
    end = add_years(st, n)
    before = [x for x in h['px'] if x[0] <= st]
    if not before or (st - before[-1][0]).days > STALE:
        fails.append(f'stale start price (last {before[-1][0] if before else "none"})')
    pts = ([before[-1]] if before else []) + [x for x in h['px'] if st < x[0] <= end]
    if pts and pts[-1][0] < end - dt.timedelta(days=GAP_BREAK):
        fails.append(f'series break: last price {pts[-1][0]}, window ends {end}')
    sales_dates = [t for t, _ in h['sales']]
    peak = max(pts[1:], key=lambda x: x[1]) if len(pts) > 1 else None
    for i, ((t0, p0), (t1, p1)) in enumerate(zip(pts, pts[1:])):
        r, gap = (p1 / p0 if p0 else 1), (t1 - t0).days
        big = r >= STEP or r <= 1 / STEP
        if gap > GAP_BREAK:
            (fails if big else warns).append(f'series break: no price {t0}..{t1} (price {r:.2f}x across it)')
            continue
        if gap > GAP_WARN:
            warns.append(f'price gap {t0}..{t1}')
        if not big:
            continue
        nxt = pts[i + 2][1] if i + 2 < len(pts) else None
        if r >= STEP and nxt and nxt / p0 <= r ** 0.5:  # the next week gives back half the move or more
            msg = f'one-week spike to {p1:g} on {t1} ({r:.2f}x up, then {nxt / p1:.2f}x)'
            (fails if group == 'fallen_winner' and (t1, p1) == peak else warns).append(msg)
            continue
        if r >= STEP and i + 2 == len(pts):
            fails.append(f'price step {r:.2f}x into the window end ({t1}), not confirmed by later prices')
            continue
        m0, m1 = at(h['mcs'], t0, 3), at(h['mcs'], t1, 3)  # same chart dates as the price
        if m0 and m1 and m0 > 0.05 and not any(t0 < d <= t1 for d in sales_dates):
            lo, hi = (m1 - 0.05) / (m0 + 0.05), (m1 + 0.05) / (m0 - 0.05)  # the ratio has one decimal
            if not lo / MISMATCH <= r <= hi * MISMATCH:
                fails.append(f'price step {r:.2f}x on {t1} vs market cap to sales {m0:g} to {m1:g} (unadjusted split/bonus?)')
        else:
            warns.append(f'price step {r:.2f}x on {t1}, market cap cannot confirm it')
    for d, subj in actions(sym):
        if st < d <= end:
            near = [x for x in pts if abs((x[0] - d).days) <= 10]
            r = max(x[1] for x in near) / min(x[1] for x in near) if len(near) > 1 else 1
            if r >= STEP:
                fails.append(f'{subj.strip()} ex {d} with a {r:.2f}x price move around it (unadjusted?)')
    if mc0 < FLOOR_NEAR:
        vals = sorted(v * (at(h['px'], t, 7) or 0) / 1e5 for t, v in h['vol'] if st - dt.timedelta(days=91) < t <= st)
        zero = 13 - sum(1 for v in vals if v > 0)
        med = vals[len(vals) // 2] if vals else 0
        if med < THIN_VALUE or zero >= THIN_ZERO:
            fails.append(f'thin trading near the floor: mc0 {mc0:.0f} cr, median weekly value {med:.1f} lakh, '
                         f'{zero} of 13 weeks without volume')
    px, mcm = o.get(f'px_{n}y'), o.get(f'mc_{n}y')
    if group in ('winner', 'fallen_winner') and px and mcm and mcm / px < 0.5:
        warns.append(f'price {px:.1f}x vs market cap {mcm:.1f}x over {n}y (market cap from screener ratios can be off: check)')
    return fails, warns

def actions(sym):
    """Split, bonus and consolidation ex-dates from the saved NSE corporate actions (scr/corporate_actions.json), if any."""
    fn = os.path.join(COMPANIES, sym, 'scr', 'corporate_actions.json')
    out = []
    if os.path.exists(fn):
        for r in (json.load(open(fn, encoding='utf-8')).get('data') or {}).get('rows') or []:
            s = r.get('subject') or ''
            if re.search(r'bonus|split|sub-division|consolidat', s, re.I):
                try:
                    out.append((dt.datetime.strptime(r['exDate'], '%d-%b-%Y').date(), s))
                except (KeyError, ValueError):
                    pass
    return out

def finalize():
    bt_dir = os.path.join(D, 'business_types')
    types = type_list()
    # 1. merge the batch files (never the *_input.csv files)
    batches = sorted((int(os.path.basename(fn)[6:-4]), fn) for fn in glob.glob(os.path.join(bt_dir, 'batch_*.csv'))
                     if os.path.basename(fn)[6:-4].isdigit())
    tags, merged, conflicts, unknown, malformed = {}, [], [], [], []
    LEVELS = ('low', 'medium', 'high')
    for b, fn in batches:
        for r in csv.DictReader(open(fn, encoding='utf-8')):
            r = {k: (r.get(k) or '').strip() for k in BT_COLS}
            r['batch'] = b
            key = (r['sym'], r['as_of'])
            t = norm_type(r['business_type'], types)
            if t is None:
                unknown.append(f"{r['sym']} {r['as_of']} '{r['business_type']}' (batch {b})")
            r['business_type'] = t or r['business_type']
            bad = [f'{k}={r[k]!r}' for k, ok in (('peers', ('helped', 'misled', 'neutral')), ('cyclicality', LEVELS),
                                                 ('capital_intensity', LEVELS), ('pricing_power', LEVELS)) if r[k] not in ok]
            if r['flag'] and not re.match(r'(shell|no real operations|unclear)\b', r['flag'], re.I):
                bad.append(f"flag {r['flag'][:50]!r}... is not shell / no real operations / unclear (still treated as a flag)")
            if bad:
                malformed.append(f"{r['sym']} {r['as_of']} (batch {b}): " + '; '.join(bad))
            if key in tags:
                if tags[key]['business_type'] != r['business_type']:
                    conflicts.append(f"{key[0]} {key[1]}: '{tags[key]['business_type']}' (batch {tags[key]['batch']}) vs "
                                     f"'{r['business_type']}' (batch {b}); first kept")
                continue
            tags[key] = r
            merged.append(r)
    with open(os.path.join(D, 'business_types.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=BT_COLS + ['batch'])
        w.writeheader()
        w.writerows(merged)
    with open(os.path.join(D, 'business_types_list.md'), 'w', encoding='utf-8') as fh:
        fh.write('# Business types\n\nWritten by `mb_sample.py --finalize` from `s2_sample.md` and `business_types/new_types*.md`.\n\n')
        fh.writelines(f'- **{name}**{": " + defn if defn else ""} ({src})\n' for name, defn, src in types)
    # 3. peers flags, overall and per batch
    peers = {}
    for r in merged:
        for k in ('all', r['batch']):
            p = peers.setdefault(k, {})
            p[r['peers'] or 'blank'] = p.get(r['peers'] or 'blank', 0) + 1
    # 2 and 4. controls, with artefact checks on winners, fallen winners and every tagged same-type candidate reached
    out_rows = {(r['sym'], r['start']): r for r in csv.DictReader(open(os.path.join(D, 'outcomes.csv'), encoding='utf-8'))}
    cand = list(csv.DictReader(open(os.path.join(D, 'sample_candidates.csv'), encoding='utf-8')))
    for r in cand:
        r['mc0'], r['multiple'] = f(r['mc0']), f(r['multiple'])
    art, flagged, sample, needs, limits, status = {}, [], [], {}, [], {}
    names = {t[0] for t in types}
    def check(r, group):
        k = (r['sym'], r['start'], r['horizon'], group)
        if k not in art:
            o = {c: f(v) for c, v in out_rows.get((r['sym'], r['start']), {}).items()}
            n = 2 if r['horizon'] == 'short' else 5 if r['horizon'] == 'medium' else \
                max((7, 10), key=lambda y: o.get(f'px_{y}y') if o.get(f'px_{y}y') is not None else -1)  # the window behind the multiple
            art[k] = artefacts(r['sym'], r['start'], n, r['mc0'], o, group)
        return art[k]
    def need(sym, as_of, group, why, w):
        e = needs.setdefault((sym, as_of), {'groups': set(), 'for': set(), 'status': set()})
        e['groups'].add(group)
        e['for'].add(w)
        e['status'].add(why)
    for w in [r for r in cand if r['group'] in ('winner', 'fallen_winner')]:
        tag = tags.get((w['sym'], w['start']))
        fails, warns = check(w, w['group'])
        wk, who = (w['sym'], w['horizon'], w['group']), f"{w['sym']} {w['horizon']}"
        if tag and tag['flag']:
            flagged.append((w, tag['flag']))
        if fails or (tag and tag['flag']):  # dropped or replaced by the orchestrator: no tags or control needed
            status[wk] = 'artefact' if fails else 'flagged'
            continue
        if not tag:
            need(w['sym'], w['start'], w['group'], 'untagged', who)
            status[wk] = 'untagged'
        elif tag['business_type'] not in names:  # the orchestrator adds the type to new_types.md or fixes the row
            status[wk] = 'type not in list'
            continue
        if w['group'] == 'fallen_winner':
            if tag:
                sample.append(dict(w, business_type=tag['business_type'], sub_type=tag['sub_type'], checks='; '.join(warns)))
            continue
        cs = [c for c in cand if c['group'] == 'control_candidate' and c['matched_to'] == w['sym'] and c['horizon'] == w['horizon']]
        if not cs:
            status[wk] = 'no candidates'
            continue
        if not tag:  # round 1 tags the nearest candidate with the winner; later ones wait for the winner's type
            if (cs[0]['sym'], cs[0]['start']) not in tags:
                need(cs[0]['sym'], cs[0]['start'], 'control_candidate', 'candidate 1', who)
            continue
        pick, skipped = None, []
        for i, c in enumerate(cs):
            ct = tags.get((c['sym'], c['start']))
            if not ct:
                need(c['sym'], c['start'], 'control_candidate', f'candidate {i + 1}', who)
                status[wk] = f'needs candidate {i + 1} ({c["sym"]})'
                break
            if ct['business_type'] != tag['business_type']:
                skipped.append(f"{c['sym']} ({ct['business_type']})")
                continue
            cf, cw = check(c, 'control')
            if ct['flag'] or cf:
                skipped.append(f"{c['sym']} (same type, {'flagged: ' + ct['flag'] if ct['flag'] else '; '.join(cf)})")
                continue
            pick = (c, ct, cw)
            break
        else:
            status[wk] = f'no same-type candidate among {len(cs)}'
        if not pick:
            status[wk] += f"; skipped {', '.join(skipped)}" if skipped else ''
            continue
        c, ct, cw = pick
        ratio = c['mc0'] / w['mc0']
        ok = c['start'] == w['start'] and 0.5 <= ratio <= 2 and c['multiple'] < H[w['horizon']][1] and c['sym'] != w['sym']
        if not ok:
            limits.append(f"- {c['sym']} for {w['sym']} {w['horizon']}: start {c['start']} vs {w['start']}, mc0 ratio {ratio:.2f}, "
                          f"multiple {c['multiple']}")
        status[wk] = f"control {c['sym']} (candidate {cs.index(c) + 1})" + (f"; skipped {', '.join(skipped)}" if skipped else '')
        if not (tag['flag'] or fails or not ok):
            sample.append(dict(w, business_type=tag['business_type'], sub_type=tag['sub_type'], control=c['sym'], checks='; '.join(warns)))
            sample.append(dict(c, group='control', business_type=ct['business_type'], sub_type=ct['sub_type'], checks='; '.join(cw)))
    # 5. outputs
    keys = ['group', 'sym', 'horizon', 'start', 'mc0', 'multiple', 'strong', 'matched_to', 'control', 'business_type', 'sub_type',
            'reason', 'checks']
    with open(os.path.join(D, 'sample.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
        wr.writeheader()
        wr.writerows(sample)
    with open(os.path.join(D, 'needs_next.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh)
        wr.writerow(['sym', 'as_of', 'groups', 'for_winner', 'status'])
        for (s, d), e in sorted(needs.items()):
            wr.writerow([s, d, ';'.join(sorted(e['groups'])), ';'.join(sorted(e['for'])), ';'.join(sorted(e['status']))])
    winners = [r for r in cand if r['group'] == 'winner']
    fallen = [r for r in cand if r['group'] == 'fallen_winner']
    cnt = lambda pre: sum(1 for k, v in status.items() if k[2] == 'winner' and v.startswith(pre))
    arts = [(k, v[0]) for k, v in art.items() if v[0]]
    warns = [(k, v[1]) for k, v in art.items() if v[1]]
    rep = ['# S2 checks', '', f'Written by `mb_sample.py --finalize`. Batches merged: {len(batches)} '
           f'({", ".join(str(b) for b, _ in batches)}); tagged rows {len(merged)}; {len(types)} types in `business_types_list.md`.', '',
           f'- Winners {len(winners)}: tagged {sum(1 for w in winners if (w["sym"], w["start"]) in tags)}; with a same-type control '
           f'{cnt("control")}; needing a next candidate {cnt("needs")}; no same-type candidate left {cnt("no same")}; '
           f'untagged {cnt("untagged")}; no candidates {cnt("no candidates")}; flagged {cnt("flagged")}; '
           f'artefact {cnt("artefact")}; type not in list {cnt("type not")}.',
           f'- Fallen winners {len(fallen)}: tagged {sum(1 for r in fallen if (r["sym"], r["start"]) in tags)}.',
           f'- sample.csv: {len(sample)} rows, ' + ', '.join(f'{g} {sum(1 for r in sample if r["group"] == g)}'
                                                         for g in ('winner', 'control', 'fallen_winner')) + '.',
           f'- needs_next.csv: {len(needs)} rows to tag next (sym, as_of, groups as in batch inputs; for_winner, status).', '',
           '## Peers flags', '', '| batch | helped | misled | neutral | misled share |', '|---|---|---|---|---|']
    for k in ['all'] + [b for b, _ in batches]:
        p = peers.get(k, {})
        rep.append(f"| {k} | {p.get('helped', 0)} | {p.get('misled', 0)} | {p.get('neutral', 0)} | "
                   f"{p.get('misled', 0) / (sum(p.values()) or 1):.0%} |")
    cells = sorted({(period(r['start']), band(r['mc0'])) for r in sample})
    rep += ['', '## Balance of sample.csv (period, size band in ₹ cr)', '',
            '| group | horizon | ' + ' | '.join(f'{p} {b}' for p, b in cells) + ' | total |', '|---|---|' + '---|' * (len(cells) + 1)]
    for g in ('winner', 'control', 'fallen_winner'):
        for hz in H:
            rs = [r for r in sample if r['group'] == g and r['horizon'] == hz]
            if rs:
                rep.append(f'| {g} | {hz} | ' + ' | '.join(str(sum(1 for r in rs if (period(r['start']), band(r['mc0'])) == c))
                                                           for c in cells) + f' | {len(rs)} |')
    in_sample = {(r['sym'], r['start']) for r in cand if r['group'] != 'control_candidate'}
    rep += ['', '## Flagged by the taggers (drop or replace)', ''] + \
           ([f"- {w['group']} {w['sym']} {w['horizon']} {w['start']}: {fl}" for w, fl in flagged] +
            [f"- candidate {r['sym']} {r['as_of']}: {r['flag']}" for r in merged if r['flag'] and (r['sym'], r['as_of']) not in in_sample]
            or ['- none'])
    rep += ['', '## Data artefacts (row left out of sample.csv; a candidate is skipped as control)', ''] + \
           ([f'- {k[3]} {k[0]} {k[2]} {k[1]}: ' + '; '.join(v) for k, v in arts] or ['- none'])
    rep += ['', '## Warnings (row kept; look if in doubt)', ''] + \
           ([f'- {k[3]} {k[0]} {k[2]} {k[1]}: ' + '; '.join(v) for k, v in warns] or ['- none'])
    rep += ['', '## Controls outside the matching limits', ''] + (limits or ['- none'])
    rep += ['', '## Malformed tag values (fix in the batch file)', ''] + ([f'- {m}' for m in malformed] or ['- none'])
    rep += ['', '## Types not in the list', ''] + ([f'- {u}' for u in unknown] or ['- none'])
    rep += ['', '## Same company and date typed differently by two batches', ''] + ([f'- {c}' for c in conflicts] or ['- none'])
    rep += ['', '## Control per winner', ''] + [f'- {k[0]} {k[1]}: {v}' for k, v in sorted(status.items()) if k[2] == 'winner']
    open(os.path.join(D, 'sample_checks.md'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('\n'.join(rep[4:9]))
    print(f'flagged {len(flagged)} | artefacts {len(arts)} | warnings {len(warns)} | outside limits {len(limits)} | '
          f'types not in list {len(unknown)} | conflicts {len(conflicts)} | malformed {len(malformed)}')
    print('wrote business_types.csv, business_types_list.md, sample.csv, needs_next.csv, sample_checks.md in', D)

if '--finalize' in a:
    finalize()
    sys.exit()
rows = [r for r in csv.DictReader(open(os.path.join(D, 'outcomes.csv'), encoding='utf-8'))]
for r in rows:
    for k, v in r.items():
        if k not in ('sym', 'start', 'last_price_date'):
            r[k] = f(v)
outc = {(r['sym'], r['start']): r for r in rows}
rows = [r for r in rows if r['mc0'] and r['mc0'] >= MIN_MC and '2006' <= r['start'][:4] <= '2023']
by_start = {}
for r in rows:
    by_start.setdefault(r['start'], []).append(r)

def pools():
    """{(group, horizon): {sym: the company's first qualifying window}} for winners and (short, medium) fallen winners."""
    P = {}
    for hz, (cols, thr, last, n) in H.items():
        yrs = cols[0].split('_')[1][:-1]
        first, fallen = {}, {}
        for r in sorted(rows, key=lambda r: r['start']):
            if r['start'] > last:
                continue
            m = mult(r, cols)
            if m is not None and m >= thr and r['sym'] not in first:
                first[r['sym']] = r
            pk, end = r.get(f'pxpeak_{yrs}y'), r.get(f'px_{yrs}y')
            if hz != 'long' and pk and end and pk >= thr and end <= pk / 2 and r['sym'] not in fallen:
                fallen[r['sym']] = r
        P[('winner', hz)] = first
        if hz != 'long':
            P[('fallen_winner', hz)] = fallen
    return P

def winner_row(w, hz):
    cols = H[hz][0]
    yrs = cols[0].split('_')[1][:-1]
    m = mult(w, cols)
    return {'group': 'winner', 'sym': w['sym'], 'horizon': hz, 'start': w['start'], 'mc0': w['mc0'], 'multiple': m,
            'strong': 'yes' if hz == 'medium' and m >= 5 else '', 'matched_to': '',
            'reason': f'{hz}: {m:.1f}x price over {"7-10" if hz == "long" else yrs} years from {w["start"]}{dilution_note(w, yrs)}'}

def fallen_row(r, hz):
    yrs = H[hz][0][0].split('_')[1][:-1]
    return {'group': 'fallen_winner', 'sym': r['sym'], 'horizon': hz, 'start': r['start'], 'mc0': r['mc0'],
            'multiple': r[f'px_{yrs}y'], 'strong': '', 'matched_to': '',
            'reason': f'{hz}: peaked at {r[f"pxpeak_{yrs}y"]:.1f}x within {yrs} years from {r["start"]}, ended at {r[f"px_{yrs}y"]:.1f}x'}

# Industry labels: screener's copy of NSE's classification in scr/overview.json `sectors`, [sector, basic industry] (a lone
# ['Diversified'] counts as both). None when the page has no label (merged/delisted) or isn't fetched yet.
_lab = {}
def label(sym):
    if sym not in _lab:
        fn = os.path.join(COMPANIES, sym, 'scr', 'overview.json')
        s = None
        if os.path.exists(fn):
            try:
                s = [x for x in json.load(open(fn, encoding='utf-8'))['data'].get('sectors') or [] if x]
            except (ValueError, KeyError, AttributeError):
                s = None
        _lab[sym] = (s[0], s[-1]) if s else None
    return _lab[sym]

def load_tags():
    """{(sym, as_of): business_type} from business_types.csv, and {type: basic industries of the labelled companies so tagged}."""
    fn = os.path.join(D, 'business_types.csv')
    tags = {(r['sym'], r['as_of']): r['business_type'] for r in csv.DictReader(open(fn, encoding='utf-8'))} if os.path.exists(fn) else {}
    ind = {}
    for (sym, _), t in tags.items():
        if label(sym):
            ind.setdefault(t, set()).add(label(sym)[1])
    return tags, ind
TAGS, TYPE_IND = load_tags()
LEVEL = {'industry': 'same basic industry', 'type': 'no industry label; same business type tag',
         'sector-level': 'sector-level: same sector, other basic industry',
         'type-industry': "winner has no industry label; a basic industry of its business type's tagged companies"}

def ranked(w, hz):
    """Every company within the matching limits (same start, mc0 0.5-2x, below the threshold), with its distance and
    industry level: tier 1 'industry' (same basic industry) or 'type' (no label, same business type tag as the winner);
    tier 2 'sector-level' (same sector) or, for a winner with no label, 'type-industry'; None when neither."""
    cols, thr = H[hz][0], H[hz][1]
    wl, wt = label(w['sym']), TAGS.get((w['sym'], w['start']))
    out = []
    for c in by_start[w['start']]:
        cm = mult(c, cols)
        if c['sym'] == w['sym'] or cm is None or cm >= thr or not (0.5 <= c['mc0'] / w['mc0'] <= 2):
            continue
        dist = abs((c['sales_g3'] or 0) - (w['sales_g3'] or 0)) / 20 + abs((c['eps_g3'] or 0) - (w['eps_g3'] or 0)) / 40 \
            + abs((c['pe0'] or 0) - (w['pe0'] or 0)) / 20 + abs(c['mc0'] / w['mc0'] - 1)
        cl, ct = label(c['sym']), TAGS.get((c['sym'], c['start']))
        if wl:
            lv = ('industry' if cl == wl else 'sector-level' if cl[0] == wl[0] else None) if cl else \
                 ('type' if wt and ct == wt else None)
        else:
            lv = None if not wt else 'type' if ct == wt else 'type-industry' if cl and cl[1] in TYPE_IND.get(wt, ()) else None
        out.append((dist, c, cm, lv))
    return sorted(out, key=lambda x: x[0])

def candidates(w, hz):
    """Control candidates: the N_CAND nearest (growth and valuation) of the winner's basic industry within the matching
    limits; when fewer, the nearest of its sector fill up ('sector-level'); still fewer are kept as they are."""
    rk = [x for x in ranked(w, hz) if x[3]]
    pick = [x for x in rk if x[3] in ('industry', 'type')][:N_CAND]
    pick += [x for x in rk if x[3] in ('sector-level', 'type-industry')][:N_CAND - len(pick)]
    return [{'group': 'control_candidate', 'sym': c['sym'], 'horizon': hz, 'start': c['start'], 'mc0': c['mc0'],
             'multiple': cm, 'strong': '', 'matched_to': w['sym'], 'match': lv,
             'reason': f'looked like {w["sym"]} at {c["start"]} (distance {dist:.2f}; {LEVEL[lv]}); reached {cm:.1f}x'}
            for dist, c, cm, lv in pick]

if '--coverage' in a:
    # How many winners in sample_candidates.csv can get N_CAND candidates with the labels present so far (writes nothing).
    src = os.path.join(D, 'sample_candidates.csv')
    ws = [r for r in csv.DictReader(open(src, encoding='utf-8')) if r['group'] == 'winner']
    full_ind, full_sec, short, none, nolab, pending = 0, 0, [], [], [], set()
    for r in ws:
        w = outc[(r['sym'], r['start'])]
        rk = ranked(w, r['horizon'])
        pending |= {c['sym'] for _, c, _, _ in rk if not os.path.exists(os.path.join(COMPANIES, c['sym'], 'scr', 'overview.json'))}
        t1 = sum(1 for x in rk if x[3] in ('industry', 'type'))
        n = len(candidates(w, r['horizon']))
        if not label(r['sym']):
            nolab.append(f"{r['sym']} {r['horizon']} (tag: {TAGS.get((r['sym'], r['start'])) or 'none'})")
        if t1 >= N_CAND:
            full_ind += 1
        elif n >= N_CAND:
            full_sec += 1
        elif n:
            short.append(f"{r['sym']} {r['horizon']} {n}")
        else:
            none.append(f"{r['sym']} {r['horizon']}")
    print(f'winners {len(ws)}: {N_CAND} same-industry candidates {full_ind}; {N_CAND} with sector-level fill {full_sec}; '
          f'fewer {len(short)}; none {len(none)}; winners without a label {len(nolab)}')
    print(f'companies within the matching limits still without overview.json: {len(pending)}')
    print('fewer:', ', '.join(short) or '-')
    print('none:', ', '.join(none) or '-')
    print('no label:', ', '.join(nolab) or '-')
    sys.exit()

P = pools()
rng = random.Random(SEED)
out, rep = [], None
if '--repair' in a:
    # Keep the old sample's winners and fallen winners that still qualify (same first qualifying window, same size band);
    # replace the rest from the same stratum (group x horizon x period x size band, seeded; never a company already a winner
    # or fallen winner in the sample, nor the one replaced); recompute every winner's candidates from the current outcomes.csv.
    src = a[a.index('--repair') + 1]
    old = list(csv.DictReader(open(src, encoding='utf-8')))
    picks = [r for r in old if r['group'] in ('winner', 'fallen_winner')]
    kept, dropped = [], []
    for r in picks:
        n = P[(r['group'], r['horizon'])].get(r['sym'])
        o = outc.get((r['sym'], r['start'])) or {}
        if '--candidates-only' in a:  # keep every pick exactly as it is; only the candidates are recomputed
            kept.append(r)
            continue
        if n and n['start'] == r['start'] and band(n['mc0']) == band(f(r['mc0'])):
            kept.append(r)
            continue
        if n and n['start'] != r['start']:
            why = (f"first qualifying window now {n['start']} (mc0 {n['mc0']:g} cr); "
                   f"at {r['start']} mc0 was {r['mc0']}, now {o.get('mc0')}")
        elif n:
            why = f"size band now {band(n['mc0'])} (mc0 {n['mc0']:g} cr, was {r['mc0']})"
        else:
            why = f"left the pool: mc0 at {r['start']} now {o.get('mc0')} cr (was {r['mc0']}), no other qualifying window with mc0 >= {MIN_MC}"
        dropped.append((r, why))
    used = {r['sym'] for r in picks}  # kept and replaced companies are never picked again
    repl, short, by_cell = {}, [], {}
    for r, why in dropped:
        by_cell.setdefault((r['group'], r['horizon'], period(r['start']), band(f(r['mc0']))), []).append(r)
    for cell in sorted(by_cell):
        g, hz, per, bd = cell
        pool = sorted((x for x in P[(g, hz)].values() if (period(x['start']), band(x['mc0'])) == (per, bd)), key=lambda x: x['sym'])
        rng.shuffle(pool)
        for r in by_cell[cell]:
            while pool and pool[-1]['sym'] in used:
                pool.pop()
            if not pool:
                short.append(f"{g} {hz} {per} {bd}: no company left for {r['sym']}")
                continue
            x = pool.pop()
            used.add(x['sym'])
            repl[(r['group'], r['sym'], r['horizon'])] = winner_row(x, hz) if g == 'winner' else fallen_row(x, hz)
    keep = {(r['group'], r['sym'], r['horizon']) for r in kept}
    old_c = {}
    for r in old:
        if r['group'] == 'control_candidate':
            old_c.setdefault((r['matched_to'], r['horizon']), []).append(r['sym'])
    changed, nearest = [], []
    for r in picks:  # in the old order, each replacement in its predecessor's place
        k = (r['group'], r['sym'], r['horizon'])
        if k in keep:
            nr = outc[(r['sym'], r['start'])]
            row = winner_row(nr, r['horizon']) if r['group'] == 'winner' else fallen_row(nr, r['horizon'])
        elif k in repl:
            row = repl[k]
        else:
            continue
        out.append(row)
        if row['group'] == 'winner':
            cs = candidates(outc[(row['sym'], row['start'])], row['horizon'])
            out += cs
            if k in keep:
                was, now = old_c.get((r['sym'], r['horizon']), []), [c['sym'] for c in cs]
                if was != now:
                    changed.append(f"- {r['sym']} {r['horizon']} {r['start']}: {', '.join(was)} -> {', '.join(now)}")
                    if was[:1] != now[:1]:
                        nearest.append(f"{r['sym']} {r['horizon']} ({(was or ['-'])[0]} -> {(now or ['-'])[0]})")
    nc = {}
    for x in out:
        if x['group'] == 'control_candidate':
            nc.setdefault((x['matched_to'], x['horizon']), []).append(x['match'])
    wins = [x for x in out if x['group'] == 'winner']
    few = [f"- {x['sym']} {x['horizon']} {x['start']}: {len(nc.get((x['sym'], x['horizon']), []))} "
           f"(label {' / '.join(label(x['sym']) or ['none'])}; tag {TAGS.get((x['sym'], x['start'])) or 'none'})"
           for x in wins if len(nc.get((x['sym'], x['horizon']), [])) < N_CAND]
    sec = [x for x in wins if any(m in ('sector-level', 'type-industry') for m in nc.get((x['sym'], x['horizon']), []))]
    rep = ['# S2 sample repair', '', f'Written by `mb_sample.py --repair` (seed {SEED}) from `{src}` and the current '
           '`outcomes.csv`. ' + ('Every pick kept as it was (--candidates-only)' if '--candidates-only' in a else
           'A pick is kept when its first qualifying window and size band are unchanged') + '; candidate lists are '
           'recomputed for every winner (same basic industry first, then sector-level).', '',
           f'- Winners and fallen winners: {len(picks)}; kept {len(kept)} (winners {sum(1 for r in kept if r["group"] == "winner")}, '
           f'fallen {sum(1 for r in kept if r["group"] == "fallen_winner")}); replaced {len(repl)}; unfilled {len(short)}.',
           f'- Kept winners whose candidate list changed: {len(changed)}; nearest candidate changed: {len(nearest)}.',
           f'- Winners with sector-level candidates: {len(sec)}; with fewer than {N_CAND} candidates: {len(few)}.', '',
           '## Replaced (old pick: why -> new pick)', ''] + \
          [f"- {r['group']} {r['sym']} {r['horizon']} {r['start']} ({period(r['start'])} {band(f(r['mc0']))}): {why} -> "
           + (f"{repl[(r['group'], r['sym'], r['horizon'])]['sym']} {repl[(r['group'], r['sym'], r['horizon'])]['start']}"
              if (r['group'], r['sym'], r['horizon']) in repl else 'unfilled') for r, why in dropped] + \
          ['', '## Unfilled', ''] + ([f'- {s}' for s in short] or ['- none']) + \
          ['', f'## Fewer than {N_CAND} candidates (count; industry label; business type tag)', ''] + (few or ['- none']) + \
          ['', '## Nearest candidate changed', ''] + ([f'- {s}' for s in nearest] or ['- none']) + \
          ['', '## Candidate lists changed (old -> new, nearest first)', ''] + (changed or ['- none'])
else:
    for hz, (cols, thr, last, n) in H.items():
        for w in pick_strat(list(P[('winner', hz)].values()), n, rng):
            out.append(winner_row(w, hz))
            out += candidates(w, hz)
        if hz in ('short', 'medium'):
            for r in pick_strat(list(P[('fallen_winner', hz)].values()), FALLEN, rng):
                out.append(fallen_row(r, hz))
        print(f'{hz}: pool {len(P[("winner", hz)])} winners')

keys = ['group', 'sym', 'horizon', 'start', 'mc0', 'multiple', 'strong', 'matched_to', 'match', 'reason']
with open(os.path.join(D, 'sample_candidates.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
    w.writeheader()
    w.writerows(out)
if rep:
    # fetch_order.txt: companies without the S2/S3 fetch (no scr/documents.json; the label-only fetch writes just
    # overview.json): new winners and fallen winners first, then
    # the other winners and fallen winners, then candidates by rank (every winner's nearest, then each one's second, ...)
    new = {(r['group'], r['sym'], r['horizon']) for r in repl.values()}
    rank = {}
    for r in out:
        if r['group'] == 'control_candidate':
            rank[(r['matched_to'], r['horizon'])] = r['_rank'] = rank.get((r['matched_to'], r['horizon']), 0) + 1
    picked = [r for r in out if r['group'] != 'control_candidate']
    seq = [r for r in picked if (r['group'], r['sym'], r['horizon']) in new] + \
          [r for r in picked if (r['group'], r['sym'], r['horizon']) not in new] + \
          sorted((r for r in out if r['group'] == 'control_candidate'), key=lambda r: r['_rank'])
    order = []
    for r in seq:
        if r['sym'] not in order and not os.path.exists(os.path.join(COMPANIES, r['sym'], 'scr', 'documents.json')):
            order.append(r['sym'])
    open(os.path.join(D, 'fetch_order.txt'), 'w', encoding='utf-8').write(''.join(s + '\n' for s in order))
    psyms = {r['sym'] for r in picked}
    rep[5:5] = [f'- fetch_order.txt: {len(order)} companies without the S2/S3 fetch (`scr/documents.json`) '
                f'({sum(1 for s in order if s in psyms)} of them winners or fallen winners).']
    open(os.path.join(D, 'sample_repair.md'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('\n'.join(rep[4:8]))
cnt = {}
for r in out:
    k = (r['group'], r['horizon'], period(r['start']), band(r['mc0']))
    cnt[k] = cnt.get(k, 0) + 1
for k in sorted(cnt):
    print(*k, cnt[k])
print('rows', len(out), '| distinct companies', len({r['sym'] for r in out}),
      '| winners without candidates:', [r['sym'] for r in out if r['group'] == 'winner'
                                        and not any(c['matched_to'] == r['sym'] and c['horizon'] == r['horizon'] for c in out)])
