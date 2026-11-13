"""A run's own bookkeeping: setup (S1), the company list (S9), the pending check (after each S14).
  python -I scripts/run.py setup <FYyyQn> --mode full|recheck [--suffix _full] [--no-sheet] [--sheet-only]
  python -I scripts/run.py list [--mode full|recheck]      (default mode: the first line of <run>/progress.md)
  python -I scripts/run.py pending [<run folder>]

---- setup (workflow/s1_setup.md) ----
Creates the run folder, sets RUN in config.py, copies the last full run's sector map in recheck mode, and points the sheet's pending tab at the run quarter. Step 4 (holdings) is kite_holdings.py.
Inputs: the quarter (the latest ended one), the mode; recheck: the newest runs/FY*/ whose progress.md starts "Mode: full".
Outputs: runs/<FYyyQn><suffix>/ with progress.md (mode line, claim line, empty checklist; recheck: where the sector map
  came from) and status.csv (header only); recheck: sector_map.md, sectors.json, sector_of.tsv copied in; RUN = '<name>'
  in scripts/config.py (only that line; checked by importing it again); the sheet (gws): the pending tab
  (sheetId 105, "Pending <FYyyQn> results") renamed to the run quarter and its rows 2+ cleared (kept as is when it
  already has that name), and its name in Data!BA1, both read back.
Refuses: a quarter name that isn't FYyyQn (n 1-4) or hasn't ended; a run folder that already has a progress.md (resume
  it instead); recheck mode with no full run ("no full run yet: run full first"). A folder without progress.md (a run
  stopped half-way) is completed. gws unavailable or failing: the local part stands, a line starting "SHEET NOT UPDATED"
  is printed, exit 0; --sheet-only redoes just the sheet step for an existing run.

---- list (workflow/s9_company_list.md) ----
Inputs (run folder, config.py): holdings.csv (S1); sector_of.tsv (S5 sectors.py order; recheck: copied from the last
  full run); full: gate/decisions.csv (gate_merge.py; NEXT rows); recheck: every company with a thesis
  (config.thesis_path: horizon, sector), the sheet's Data tab tickers (Data!A2:A300 through gws) as a cross-check when
  the sheet can be read, sectors.json marker states.
Full: every holding plus every gate NEXT; order: holdings, then sector rank (lowest first), then the gate's est_cagr
  (highest first); why "holding" / "gate NEXT, sector <id> rank <n>"; horizon: the thesis's (holdings) or the gate's.
Recheck: every holding, every company with a thesis and any Data-tab ticker without one; horizon from its thesis; order: holdings, then companies whose sector
  has a broken marker in sectors.json, then sector rank; why "holding" / "listed" / "sector <id> marker broken", plus
  "no thesis: re-analyse" when the thesis file is missing.
Outputs: <run>/company_list.csv (sym, name, held, sector, sector_rank, horizon, order, why); a status.csv row per company
  (phase S10, state queued) unless it has one. Re-running rewrites the list and adds no duplicate status rows.
Stops (exit 1, nothing written) on a NEXT or holding with no sector_of.tsv row (listed). An unreadable sheet in recheck
  mode prints "SHEET NOT READ" and the list comes from the theses and holdings alone.

---- pending ----
Lists the companies in <run>/company_list.csv that haven't finished S14 (status.csv phase S14, state done) and prints
  PENDING: <n>.
"""
import argparse, datetime as dt, glob, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_lib as W
from config import all_runs, company_runs_dir, run_dir, run_path, thesis_path

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(SCRIPTS, 'config.py')
STATUS_HEADER = 'sym,phase,state,stage,loops_to_s10,results_used,updated,note\n'
COPY = ('sector_map.md', 'sectors.json', 'sector_of.tsv')
PENDING_ID, PENDING_RE = 105, re.compile(r'^Pending .* results$')
PENDING_HEADER = ['Ticker', 'Name', 'Latest declared quarter', 'Results due by', 'Notes']
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def first_line(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.readline().strip()
    except OSError:
        return ''


def last_full_run(exclude):
    """The newest run folder (by name: quarter, then _full) whose progress.md says Mode: full."""
    runs = [d for d in all_runs() if W.RUN_RE.match(os.path.basename(d))]
    for d in reversed(runs):
        if os.path.basename(d) != exclude and first_line(os.path.join(d, 'progress.md')) == 'Mode: full':
            return d
    return None


def set_config_run(name):
    text = open(CONFIG, encoding='utf-8').read()
    new, n = re.subn(r"^RUN = '[^']*'", f"RUN = '{name}'", text, count=1, flags=re.M)
    if n != 1:
        W.fail(f"{CONFIG}: no line starting RUN = '...' to set")
    if new != text:
        W.write_text(CONFIG, new)
    r = subprocess.run([sys.executable, '-I', '-c', f'import sys; sys.path.insert(0, {SCRIPTS!r}); import config; print(config.RUN)'],
                       capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != 'RUN'})
    if r.returncode != 0 or r.stdout.strip() != name:
        W.fail(f'config.py check failed: RUN reads {r.stdout.strip()!r} ({r.stderr.strip()[:200]})')


def progress_text(name, mode, source):
    now = dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M')
    lines = [f'Mode: {mode}', 'Orchestrator: <session or thread>, since <time>, last update <time>',
             f'Created {now} IST by run.py setup']
    if source:
        lines.append(f'Sector map from: {source} (sector_map.md, sectors.json, sector_of.tsv copied)')
    lines += ['', '## Checklist', 'Done:', 'Running (with tier):', 'Next:', 'Open items for the user:', '']
    return '\n'.join(lines)


def sheet_step(q):
    """Rename the pending tab to the run quarter, clear its rows, write its name to Data!BA1; read both back."""
    name = f'Pending {q} results'
    try:
        tabs = W.sheet_meta()
        old = next((t for t, i in tabs.items() if i == PENDING_ID), None) or \
            next((t for t in tabs if PENDING_RE.match(t)), None)
        if old is None:
            W.sheet_batch([{'addSheet': {'properties': {'sheetId': PENDING_ID, 'title': name,
                                                        'gridProperties': {'frozenRowCount': 1}}}}])
            W.sheet_put([(f'{W.quote_tab(name)}!A1:E1', [PENDING_HEADER])])
            what = f'tab "{name}" created (no pending tab found)'
        elif old != name:
            W.sheet_batch([{'updateSheetProperties': {'properties': {'sheetId': tabs[old], 'title': name}, 'fields': 'title'}}])
            W.sheet_clear([f'{W.quote_tab(name)}!A2:F'])
            what = f'tab "{old}" renamed "{name}", its rows cleared'
        else:
            what = f'tab "{name}" already current, kept'
        W.sheet_put([('Data!BA1', [[name]])])
        after = W.sheet_meta()
        ba1, = W.sheet_get(['Data!BA1'])
    except W.gws_mod().SheetError as e:
        return f'SHEET NOT UPDATED ({e})'
    got = ba1[0][0] if ba1 and ba1[0] else ''
    if name not in after or got != name:
        return f'SHEET NOT UPDATED (read-back: tab present {name in after}, Data!BA1 = {got!r})'
    return f'sheet: {what}; Data!BA1 = "{name}" (read back)'


def cmd_setup(a):
    try:
        end = W.fyq_end(a.quarter)
    except ValueError as e:
        W.fail(str(e))
    if end > dt.date.today():
        W.fail(f'{a.quarter} ends {end}: not over yet (a run is named after the latest ended quarter)')
    name = a.quarter + a.suffix
    run = run_path(name)
    prog = os.path.join(run, 'progress.md')
    if a.sheet_only:
        if not os.path.exists(prog):
            W.fail(f'{run} has no progress.md: run the setup first')
        msg = sheet_step(a.quarter)
        print(msg)
        return 0
    if not a.mode:
        W.fail('--mode full|recheck is required')
    if os.path.exists(prog):
        W.fail(f'{run} already exists with a progress.md: resume that run (how to resume: workflow/orchestrator.md) instead')
    if a.suffix and not os.path.isdir(run_path(a.quarter)):
        print(f'note: no runs/{a.quarter}/ yet; the suffix is for a second run in the same quarter')
    source = None
    if a.mode == 'recheck':
        source = last_full_run(exclude=name)
        if not source:
            W.fail('no full run yet: run full first')
        missing = [f for f in COPY if not os.path.exists(os.path.join(source, f))]
        if missing:
            W.fail(f'{source} (the last full run) lacks {missing}: finish its S5 first')
    os.makedirs(run, exist_ok=True)
    sp = os.path.join(run, 'status.csv')
    if not os.path.exists(sp):
        W.write_text(sp, STATUS_HEADER)
    for f in COPY if source else ():
        tmp = os.path.join(run, f + '.tmp')
        shutil.copyfile(os.path.join(source, f), tmp)
        os.replace(tmp, os.path.join(run, f))
    set_config_run(name)
    W.write_text(prog, progress_text(name, a.mode, source))  # last: its presence marks the local part done
    print(f'run folder {run} ready: mode {a.mode}' + (f', sector map copied from {source}' if source else '') +
          f"; config.py RUN = '{name}'")
    if a.no_sheet:
        print('sheet step skipped (--no-sheet)')
        return 0
    msg = sheet_step(a.quarter)
    with open(prog, 'a', encoding='utf-8') as fh:
        fh.write(f'S1 sheet: {msg}\n')
    print(msg)
    return 0


# ---------- list ----------
LIST_FIELDS = ['sym', 'name', 'held', 'sector', 'sector_rank', 'horizon', 'order', 'why']
SFIELDS = ['sym', 'phase', 'state', 'stage', 'loops_to_s10', 'results_used', 'updated', 'note']


def cmd_list(a):
    run = run_dir()
    mode = a.mode
    if not mode:
        try:
            first = open(os.path.join(run, 'progress.md'), encoding='utf-8').readline().strip()
        except OSError:
            first = ''
        mode = first.replace('Mode:', '').strip() if first.startswith('Mode:') else ''
        if mode not in ('full', 'recheck'):
            W.fail(f'no mode: pass --mode, or start {run}/progress.md with "Mode: full|recheck"')
    hp = os.path.join(run, 'holdings.csv')
    if not os.path.exists(hp):
        W.fail(f'{hp} missing: S1 copies the holdings there')
    hold = {r['sym']: r for r in W.read_csv(hp)}
    sp = os.path.join(run, 'sector_of.tsv')
    if not os.path.exists(sp):
        W.fail(f'{sp} missing: run sectors.py order (full) or copy it from the last full run (recheck)')
    sec = {r['sym']: r for r in W.read_csv(sp, delimiter='\t')}
    other_rank = max([W.fnum(r['rank']) or 0 for r in sec.values()] + [0]) + 1

    def thesis(sym):
        p = thesis_path(sym)
        try:
            return W.read_json(p) if os.path.exists(p) else None
        except ValueError:
            return None

    def name(sym):
        return (hold.get(sym) or {}).get('name') or (sec.get(sym) or {}).get('name') or (W.scr(sym, 'overview') or {}).get('name') or ''
    rows, missing = [], []
    if mode == 'full':
        dp = os.path.join(run, 'gate', 'decisions.csv')
        if not os.path.exists(dp):
            W.fail(f'{dp} missing: run gate_merge.py after the last S8R')
        nxt = [r for r in W.read_csv(dp) if r.get('decision') == 'NEXT']
        for s in hold:
            if s not in sec:
                missing.append(f'{s} (holding)')
        for r in nxt:
            if r['sym'] not in sec and r['sym'] not in hold:
                missing.append(r['sym'])
        if missing:
            W.fail(f'no sector_of.tsv row for {missing}: re-run sectors.py order --from-gate')
        for s in hold:
            t = thesis(s)
            rows.append({'sym': s, 'held': True, 'sector': sec[s]['sector'], 'sector_rank': W.fnum(sec[s]['rank']),
                         'horizon': (t or {}).get('horizon', ''), 'why': 'holding', 'k': (0, 0, 0)})
        for r in nxt:
            s = r['sym']
            if s in hold:
                continue
            rk = W.fnum(sec[s]['rank'])
            rows.append({'sym': s, 'held': False, 'sector': sec[s]['sector'], 'sector_rank': rk, 'horizon': r.get('horizon') or '',
                         'why': f"gate NEXT, sector {sec[s]['sector']} rank {sec[s]['rank']}",
                         'k': (1, rk, -(W.fnum(r.get('est_cagr')) or -99))})
    else:
        # every company with a thesis (runs/companies/), plus the sheet's Data tab as a cross-check when readable
        root = company_runs_dir()
        theses = sorted(x for x in (os.listdir(root) if os.path.isdir(root) else ()) if os.path.exists(thesis_path(x)))
        try:
            v, = W.sheet_get(['Data!A2:A300'])
            sheet = [str(r[0]).strip() for r in v if r and str(r[0]).strip()]
        except W.gws_mod().SheetError as e:
            sheet = []
            print(f'SHEET NOT READ ({e}): listed from {root} and the holdings only')
        extra = [x for x in sheet if x not in theses and x not in hold]
        if extra:
            print(f'in the Data tab without a thesis: {extra}')
        listed = theses + extra
        mp = os.path.join(run, 'sectors.json')
        broken = set()
        if os.path.exists(mp):
            for s in W.read_json(mp).get('sectors') or []:
                if any(m.get('state') == 'broken' for m in s.get('markers') or []):
                    broken.add(s['id'])
        for s in dict.fromkeys(list(hold) + listed):
            t = thesis(s)
            sector = (sec.get(s) or {}).get('sector') or (t or {}).get('sector') or 'other'
            rk = W.fnum((sec.get(s) or {}).get('rank')) or other_rank
            why = ['holding' if s in hold else 'listed']
            if sector in broken:
                why.append(f'sector {sector} marker broken')
            if not t:
                why.append('no thesis: re-analyse')
            rows.append({'sym': s, 'held': s in hold, 'sector': sector, 'sector_rank': rk, 'horizon': (t or {}).get('horizon', ''),
                         'why': '; '.join(why), 'k': (0 if s in hold else 1 if sector in broken else 2, rk, s)})
    rows.sort(key=lambda r: r['k'])
    for i, r in enumerate(rows, 1):
        r['order'], r['name'] = i, name(r['sym'])
        r['sector_rank'] = '' if r['sector_rank'] is None else int(r['sector_rank'])
    W.write_csv(os.path.join(run, 'company_list.csv'), LIST_FIELDS, rows)
    stp = os.path.join(run, 'status.csv')
    have = {r['sym'] for r in W.read_csv(stp)} if os.path.exists(stp) else set()
    now = dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M')
    add = [{'sym': r['sym'], 'phase': 'S10', 'state': 'queued', 'updated': now} for r in rows if r['sym'] not in have]
    if add:
        W.append_csv(stp, SFIELDS, add)
    print(f'{mode}: {len(rows)} companies ({sum(r["held"] for r in rows)} holdings) -> {os.path.join(run, "company_list.csv")}; '
          f'{len(add)} status rows added; no thesis: {[r["sym"] for r in rows if "no thesis" in r["why"]] or "none"}')
    return 0


# ---------- pending ----------
def cmd_pending(a):
    run = a.run or run_dir()
    cp = os.path.join(run, 'company_list.csv')
    if not os.path.exists(cp):
        W.fail(f'{cp} missing: run S9 (run.py list) first')
    companies = [r['sym'] for r in W.read_csv(cp)]
    sp = os.path.join(run, 'status.csv')
    status = {r['sym']: r for r in W.read_csv(sp)} if os.path.exists(sp) else {}
    pending = []
    for s in companies:
        r = status.get(s)
        if not r or not (r['phase'] == 'S14' and r['state'] == 'done'):
            pending.append((s, r['phase'] if r else '-', r['state'] if r else 'not started', r.get('stage', '') if r else ''))
    for s, phase, state, stage in pending:
        print(f'{s}\t{phase}\t{state}\t{stage}')
    print(f'PENDING: {len(pending)}')
    return 0


def doc_part(head):
    """A mode's --help: the docstring's usage lines plus its '---- <head>' section."""
    parts = __doc__.split('\n---- ')
    return parts[0] + '\n---- ' + next(p for p in parts[1:] if p.startswith(head))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True, help='the mode; <mode> --help for its own help')
    p = sp.add_parser('setup', help='create the run folder (S1)', description=doc_part('setup'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('quarter', help='the run quarter, FYyyQn (the latest ended one)')
    p.add_argument('--mode', choices=['full', 'recheck'], help='the run mode (required unless --sheet-only)')
    p.add_argument('--suffix', default='', choices=['', '_full'], help="folder name suffix (default: none)")
    p.add_argument('--no-sheet', action='store_true', help='skip the sheet step')
    p.add_argument('--sheet-only', action='store_true', help='only the sheet step, for an existing run')
    p = sp.add_parser('list', help='write the company list (S9)', description=doc_part('list'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--mode', choices=['full', 'recheck'], help='default: the first line of <run>/progress.md')
    p = sp.add_parser('pending', help='list companies not done with S14', description=doc_part('pending'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('run', nargs='?', help='run folder (default: the current run, config.py)')
    a = ap.parse_args()
    return {'setup': cmd_setup, 'list': cmd_list, 'pending': cmd_pending}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
