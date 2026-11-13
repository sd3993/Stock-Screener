"""S14 and S16 by script: writes agreed analyses and allocation decisions into the Google Sheet through the gws
CLI (RAW values), reads every written cell back and compares it. Layout: sources/sheet.md.
  python -I scripts/sheet_write.py listing SYM... [--hold SYM...] [--dry-run]     (S14, workflow/s14_listing.md)
  python -I scripts/sheet_write.py allocation [--dry-run]                         (S16, workflow/s15_allocation.md)
listing inputs: each company's agreed analysis (thesis.py's agreed(): the highest recheck<N>.json in its newest
  runs/companies/<SYM>/<FYyyQn>/ folder), its scr/overview.json (stored price, name, NSE/BSE code; run scr_company.py
  --only overview first), the run quarter, runs/verdict_history.csv. --hold SYM: an S11 "hold": only a verdict-history
  row ("markers held, results <run quarter>"), copied from the company's last row.
listing writes, per company: its Data row (found by ticker in A2:A300, else the first empty row; none: "NO FREE ROW",
  that company skipped) in A:AC, BB:BC and BE:BF (columns in DATA in the script); then once for the batch: the Data Flags tab
  (A2:G) rewritten with the listed tickers' old rows replaced by their analyses' data flags, sorted by ticker; the
  pending tab (its name in Data!BA1, A2:E) with each listed company added when its results_used is before the run
  quarter and removed otherwise; one runs/verdict_history.csv row per company (the reason: the analysis's what_changed
  line, else first listing / changed from the previous verdict / unchanged on newer results).
allocation inputs: <run>/allocation/recheck<N>.json (highest N; the S15 format in workflow/s15_allocation.md) and
  <run>/holdings.csv. Writes Holdings F (status) and M (notes) on each holding's row (found by ticker in Z); clears the
  written columns of sold rows (Qty 0: B, C, D, F, M, N, O, P, Q, V, Z; never deletes a row); rewrites the Allocation
  block rows 2-100, columns B, C, D, E, H, I, N, Z (rows past the last position cleared); checks the Holdings data
  columns C (qty) and D (avg cost) against <run>/holdings.csv and reports any difference (exit 4), writing neither.
Safety: every written column is checked against the formula columns listed in sources/sheet.md;
  one in the map stops the script before any write. Writes go in one values.batchUpdate per company (Data) and one per
  tab block, so a failure never leaves half a row. After writing, every written range is read back and compared cell
  by cell (numbers as numbers, text exactly); a difference is rewritten once, then the script fails (exit 4) naming
  the cells. gws missing or an auth error: exit 2, nothing written after the failing call.
--dry-run: reads the sheet (no writes) and saves the exact write plan (every range and its values, plus the read-back
  expectations) to <run>/sheet_plan_<listing|allocation>_<time>.json, and prints a summary. The plan is what a light-tier
  subagent would apply if the script can't run.
"""
import argparse, datetime as dt, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_lib as W
from config import run_dir, shared_path

DATA_FIRST, DATA_LAST = 2, 300
DATA = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
        'X', 'Y', 'Z', 'AA', 'AB', 'AC', 'BB', 'BC', 'BE', 'BF']
VH_FIELDS = ['date', 'quarter_folder', 'sym', 'results_used', 'verdict', 'reason']
HOLD_FIRST, HOLD_LAST = 2, 100
SOLD_CLEAR = ['B', 'C', 'D', 'F', 'M', 'N', 'O', 'P', 'Q', 'V', 'Z']
ALLOC_COLS = ['B', 'C', 'D', 'E', 'H', 'I', 'N', 'Z']
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


class Fail(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


def formula_cols(path=os.path.join('sources', 'sheet.md')):
    """{tab: set of column letters} from the "Formula columns" line of sources/sheet.md, e.g. "Data AD:AZ, BA, BD; ..."."""
    txt = open(path, encoding='utf-8').read()
    m = re.search(r'\*\*Formula columns \(never written\):\*\*\s*(.+)', txt)
    if not m:
        raise Fail(f'{path}: no "Formula columns (never written):" line to check the column map against', 1)
    out = {}
    for part in m.group(1).split(';'):
        part = part.strip().rstrip('.')
        if not part:
            continue
        tab, cols = part.split(' ', 1)
        s = set()
        for c in cols.split(','):
            c = c.strip()
            if ':' in c:
                a, b = c.split(':')
                s |= {W.col_letters(i) for i in range(W.col_index(a), W.col_index(b) + 1)}
            elif c:
                s.add(c)
        out[tab] = s
    return out


def check_map(tab, cols, fc):
    bad = sorted(set(cols) & fc.get(tab, set()), key=W.col_index)
    if bad:
        raise Fail(f'REFUSED: the {tab} column map includes formula columns {bad} (formula columns: sources/sheet.md)', 1)


def num_or_blank(x):
    return '' if x is None else x


def data_row(a, ov, run_q):
    """The Data row's written cells {column: value} for one agreed analysis."""
    hz, holds = a.get('horizon'), a.get('horizon_holds', True) is not False
    flag = lambda h: 'Y' if (h == hz and holds) else 'N'
    part = lambda h, k: num_or_blank((a.get(h) or {}).get(k))
    nse, bse = (ov or {}).get('nse_code'), (ov or {}).get('bse_code')
    code = nse or bse or a['sym']
    kill = ' '.join(x for x in (str(a.get('kill_condition') or ''), f"Review: {a['review_date']}" if a.get('review_date') else '') if x)
    return {
        'A': a['sym'], 'B': f'NSE:{nse}' if nse else f'BOM:{bse}' if bse else f'NSE:{a["sym"]}',
        'C': f'https://www.screener.in/company/{code}/consolidated/', 'D': (ov or {}).get('name') or a.get('name') or '',
        'E': a.get('sector') or '', 'F': a.get('results_used') or '', 'G': a.get('analysed_on') or '',
        'H': num_or_blank((ov or {}).get('current_price')), 'I': num_or_blank(a.get('eps_ttm_normalised')),
        'J': num_or_blank(a.get('eps_y1_base')),
        'K': flag('short'), 'L': part('short', 'eps_y2_base'), 'M': part('short', 'eps_y2_bear'), 'N': part('short', 'exit_pe'),
        'O': flag('medium'), 'P': part('medium', 'eps_y5_base'), 'Q': part('medium', 'eps_y5_bear'), 'R': part('medium', 'exit_pe'),
        'S': flag('long'), 'T': part('long', 'eps_y7_base'), 'U': part('long', 'eps_y7_bear'), 'V': part('long', 'exit_pe'),
        'W': num_or_blank(a.get('dividend_per_share_per_year')), 'X': a.get('evidence_quality') or '',
        'Y': a.get('nonneg_overall') or '', 'Z': '; '.join(map(str, a.get('bent_rules') or [])), 'AA': a.get('thesis') or '',
        'AB': kill, 'AC': a.get('_file', ''), 'BB': '' if holds else (hz or ''),
        'BC': ', '.join(map(str, a.get('nonneg_failed') or [])), 'BE': hz or '', 'BF': a.get('discovery_stage') or ''}


def row_ranges(tab, row, cells):
    """Contiguous column runs of {col: value} on one row -> [(range, [[values]])]."""
    cols = sorted(cells, key=W.col_index)
    out, run = [], []
    for c in cols:
        if run and W.col_index(c) != W.col_index(run[-1]) + 1:
            out.append(run)
            run = []
        run.append(c)
    if run:
        out.append(run)
    q = W.quote_tab(tab)
    return [(f'{q}!{r[0]}{row}:{r[-1]}{row}', [[cells[c] for c in r]]) for r in out]


def same(a, b):
    """A written value against its read-back (RAW: text stays text, numbers numbers, booleans booleans)."""
    if a in ('', None) and b in ('', None):
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-9 * max(1, abs(a))
    return type(a) is type(b) and a == b


def readback(plan):
    """Cells in plan whose sheet value differs: [(range, i, j, expected, got)]."""
    got = W.sheet_get([r for r, _ in plan])
    bad = []
    for (rng, vals), g in zip(plan, got):
        for i, row in enumerate(vals):
            for j, v in enumerate(row):
                gv = g[i][j] if i < len(g) and j < len(g[i]) else ''
                if not same(v, gv):
                    bad.append((rng, i, j, v, gv))
    return bad


def apply(plan, dry, kind, run, extra=None):
    """Write the plan in one batch, read back, rewrite once, fail on a second difference; or save it (--dry-run)."""
    if dry:
        p = os.path.join(run, f'sheet_plan_{kind}_{dt.datetime.now(IST):%Y%m%d_%H%M%S}.json')
        W.write_json(p, {'kind': kind, 'value_input_option': 'RAW', 'writes': [{'range': r, 'values': v} for r, v in plan],
                         'read_back': 'read every range with valueRenderOption UNFORMATTED_VALUE and compare cell by cell',
                         **(extra or {})})
        return p
    W.sheet_put(plan)
    bad = readback(plan)
    if bad:
        redo = {r for r, *_ in bad}
        W.sheet_put([x for x in plan if x[0] in redo])
        bad = readback(plan)
        if bad:
            raise Fail('READ-BACK MISMATCH after one rewrite: ' + '; '.join(f'{r} [{i},{j}] wrote {v!r} got {g!r}' for r, i, j, v, g in bad[:10]), 4)
    return None


def cmd_listing(a):
    run = run_dir()
    rq = re.sub(r'_full$', '', os.path.basename(os.path.normpath(run)))
    fc = formula_cols()
    check_map('Data', DATA, fc)
    check_map('Data Flags', list('ABCDEFG'), fc)
    import thesis as TH
    ana, skipped = {}, []
    for s in a.syms:
        fn, why = TH.agreed(s)
        if not fn:
            skipped.append(f'{s}: {why}')
            continue
        d = W.read_json(fn)
        d['_file'] = fn.replace('\\', '/')
        d.setdefault('sym', s)
        ana[s] = d
    if skipped:
        raise Fail('no agreed analysis: ' + '; '.join(skipped), 1)
    vh_path = shared_path('verdict_history.csv')
    vh = W.read_csv(vh_path) if os.path.exists(vh_path) else []
    today = dt.date.today().isoformat()
    vh_rows = []
    for s in a.hold or []:
        prev = [r for r in vh if r['sym'] == s]
        if not prev:
            raise Fail(f'--hold {s}: no earlier verdict-history row to carry forward', 1)
        vh_rows.append({'date': today, 'quarter_folder': os.path.basename(os.path.normpath(run)), 'sym': s,
                        'results_used': prev[-1]['results_used'], 'verdict': prev[-1]['verdict'], 'reason': f'markers held, results {rq}'})
    plans, report = [], []
    if ana:
        tick, ba1, flags = W.sheet_get(['Data!A2:A300', 'Data!BA1', "'Data Flags'!A2:G500"])
        pend_name = ba1[0][0] if ba1 and ba1[0] else ''
        if not re.match(r'^Pending .* results$', str(pend_name)):
            raise Fail(f'Data!BA1 holds {pend_name!r}, not a pending tab name: run run.py setup --sheet-only', 1)
        pq = W.quote_tab(pend_name)
        pend, = W.sheet_get([f'{pq}!A2:E500'])
        rows = {str(r[0]): DATA_FIRST + i for i, r in enumerate(tick) if r and str(r[0]).strip()}
        used = set(rows.values())
        free = [r for r in range(DATA_FIRST, DATA_LAST + 1) if r not in used]
        nofree = []
        for s, an in ana.items():
            ov = W.scr(s, 'overview')
            if ov is None:
                report.append(f'{s}: no scr/overview.json: stored price, name and code missing (run scr_company.py --only overview)')
            r = rows.get(s)
            if r is None:
                if not free:
                    report.append(f'NO FREE ROW for {s} (Data rows {DATA_FIRST}-{DATA_LAST} full); not written')
                    nofree.append(s)
                    continue
                r = free.pop(0)
            plans.append((s, row_ranges('Data', r, data_row(an, ov, rq))))
            report.append(f'{s}: Data row {r}')
            prev = [x for x in vh if x['sym'] == s]
            verdict = (f"{an.get('horizon')}{'' if an.get('horizon_holds', True) is not False else ' (horizon test fails)'}, "
                       f"{an.get('discovery_stage')}, non-negotiables {an.get('nonneg_overall')}")
            reason = an.get('what_changed') or ('first listing' if not prev else f"changed from: {prev[-1]['verdict']}" if prev[-1]['verdict'] != verdict
                      else f"unchanged on results {an.get('results_used')} ({an['_file']})")
            vh_rows.append({'date': today, 'quarter_folder': os.path.basename(os.path.normpath(run)), 'sym': s,
                            'results_used': an.get('results_used'), 'verdict': verdict, 'reason': reason})
        for s in nofree:  # not listed: its flags, pending row and verdict wait for a free row
            ana.pop(s)
        # Data Flags: drop the listed tickers' rows, add theirs, sort by ticker, rewrite A2:G (blank rows past the end)
        keep = [r + [''] * (7 - len(r)) for r in flags if r and str(r[0]) not in ana]
        for s, an in ana.items():
            for i, f in enumerate(an.get('data_flags') or [], 1):
                keep.append([s, i, f.get('item', ''), f.get('what_disagreed', ''), str(f.get('values_seen', '')),
                             str(f.get('value_used_and_why', '')), f.get('type', '')])
        keep.sort(key=lambda r: (str(r[0]), W.fnum(r[1]) or 0))
        n_old = len(flags)
        block = keep + [[''] * 7] * max(0, n_old - len(keep))
        tab_plan = []
        if block:
            tab_plan.append((f"'Data Flags'!A2:G{len(block) + 1}", block))
        # pending tab
        pend_rows = [r + [''] * (5 - len(r)) for r in pend if r and str(r[0]) not in ana]
        for s, an in ana.items():
            ru = an.get('results_used') or ''
            try:
                behind = W.fyq_index(ru) < W.fyq_index(rq)
            except ValueError:
                behind = True
            if behind:
                end = W.fyq_end(rq)
                due = end + dt.timedelta(days=60 if rq.endswith('Q4') else 45)
                pend_rows.append([s, (W.scr(s, 'overview') or {}).get('name') or an.get('name', ''), ru, due.isoformat(),
                                  f'analysed on {ru} results; re-run after {rq} results'])
        pend_rows.sort(key=lambda r: str(r[0]))
        pblock = pend_rows + [[''] * 5] * max(0, len(pend) - len(pend_rows))
        if pblock:
            tab_plan.append((f'{pq}!A2:E{len(pblock) + 1}', pblock))
        report.append(f'data flags rows {len(keep)} (was {n_old}); pending rows {len(pend_rows)} (was {len(pend)})')
        plans.append(('_tabs', tab_plan))
    saved = []
    for s, plan in plans:
        if plan:
            p = apply(plan, a.dry_run, f'listing_{s}', run)
            if p:
                saved.append(p)
    if a.dry_run:
        p = os.path.join(run, f'sheet_plan_listing_verdicts_{dt.datetime.now(IST):%Y%m%d_%H%M%S}.json')
        W.write_json(p, {'append_to': vh_path, 'rows': vh_rows})
        saved.append(p)
    elif vh_rows:
        W.append_csv(vh_path, VH_FIELDS, vh_rows)
    for x in report:
        print(x)
    print(f'{len(ana)} listed, {len(a.hold or [])} hold rows; ' + (f'DRY RUN, plans: {saved}' if a.dry_run else
                                                                    f'written and read back; {len(vh_rows)} verdict-history rows'))
    return 3 if any(x.startswith('NO FREE ROW') for x in report) else 0


def cmd_allocation(a):
    run = run_dir()
    fc = formula_cols()
    check_map('Holdings', ['F', 'M'] + SOLD_CLEAR, fc)
    check_map('Allocation', ALLOC_COLS, fc)
    files = sorted(((int(m.group(1)), f) for f in glob.glob(os.path.join(run, 'allocation', 'recheck*.json'))
                    if (m := re.search(r'recheck(\d+)\.json$', f))))
    if not files:
        raise Fail(f'no {os.path.join(run, "allocation", "recheck<N>.json")}: the allocation rechecks come first', 1)
    d = W.read_json(files[-1][1])
    hold_dec, alloc = d.get('holdings') or [], d.get('allocation') or []
    if len(alloc) > HOLD_LAST - 1:
        raise Fail(f'{len(alloc)} allocation rows: more than rows 2-{HOLD_LAST}', 1)
    v, = W.sheet_get([f'Holdings!A{HOLD_FIRST}:Z{HOLD_LAST}'])
    rows = {}
    for i, r in enumerate(v):
        z = r[25] if len(r) > 25 else ''
        if z:
            rows[str(z)] = (HOLD_FIRST + i, r[2] if len(r) > 2 else '')
    plan, notes = [], []
    for h in hold_dec:
        hit = rows.get(h['sym'])
        if not hit:
            notes.append(f'holding {h["sym"]} not on the Holdings tab (run kite_holdings.py): not written')
            continue
        r = hit[0]
        plan += [(f'Holdings!F{r}', [[h.get('status', '')]]), (f'Holdings!M{r}', [[h.get('notes', '')]])]
    decided = {h['sym'] for h in hold_dec}
    for sym, (r, qty) in rows.items():
        if qty in (0, '0') and sym not in decided:
            plan += [(f'Holdings!{c}{r}', [['']]) for c in SOLD_CLEAR]
            notes.append(f'sold {sym}: row {r} cleared')
    for i in range(HOLD_LAST - 1):
        r = HOLD_FIRST + i
        x = alloc[i] if i < len(alloc) else {}
        cells = {'B': x.get('name', ''), 'C': x.get('action', ''), 'D': num_or_blank(x.get('target_weight')) if x else '',
                 'E': num_or_blank(x.get('target_value')) if x else '', 'H': num_or_blank(x.get('buy_below')) if x else '',
                 'I': num_or_blank(x.get('sell_above')) if x else '', 'N': x.get('notes', ''), 'Z': x.get('sym', '')}
        plan += row_ranges('Allocation', r, cells)
    # the Holdings data columns (kite_holdings.py's) against <run>/holdings.csv: reported, never written here
    hp = os.path.join(run, 'holdings.csv')
    mism = []
    for h in (W.read_csv(hp) if os.path.exists(hp) else []):
        hit = rows.get(h['sym'])
        sv = v[hit[0] - HOLD_FIRST] if hit else []
        q, c = (sv[2] if len(sv) > 2 else None), (sv[3] if len(sv) > 3 else None)
        if not hit or W.fnum(q) != W.fnum(h['qty']) or abs((W.fnum(c) or 0) - (W.fnum(h['avg_cost']) or 0)) > 1e-6:
            mism.append(f"{h['sym']}: sheet qty {q} avg {c}, holdings.csv {h['qty']} {h['avg_cost']}")
    p = apply(plan, a.dry_run, 'allocation', run, {'source': files[-1][1]})
    for n in notes:
        print(n)
    for m in mism:
        print('HOLDINGS DIFFER (run kite_holdings.py, then this again): ' + m)
    print(f'{len(hold_dec)} holdings, {len(alloc)} allocation rows from {files[-1][1]}; ' + (f'DRY RUN, plan: {p}' if p else 'written and read back'))
    return 4 if mism else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True, help='the mode; <mode> --help for its own help')
    p = sp.add_parser('listing', help='agreed analyses into the Data tab and related tabs (S14)', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('syms', nargs='*', help='companies to list (give SYMs, --hold SYMs or both)')
    p.add_argument('--hold', nargs='*', default=[], help='S11 "hold" companies: only a verdict-history row')
    p.add_argument('--dry-run', action='store_true', help='read the sheet, save the write plan, write nothing')
    p = sp.add_parser('allocation', help='allocation decisions into the Holdings and Allocation tabs (S16)', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dry-run', action='store_true', help='read the sheet, save the write plan, write nothing')
    a = ap.parse_args()
    if a.cmd == 'listing' and not (a.syms or a.hold):
        W.fail('give the companies to list, or --hold SYM...')
    try:
        return cmd_listing(a) if a.cmd == 'listing' else cmd_allocation(a)
    except Fail as e:
        print(str(e), file=sys.stderr)
        return e.code
    except W.gws_mod().SheetError as e:
        print(f'SHEET ERROR (nothing written after this call): {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
