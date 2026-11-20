"""S6R: merges the gate decisions; with watch-check, checks the price watches against today's prices.
  python -I scripts/gate_merge.py                (S6R: decisions.csv and the price watches)
  python -I scripts/gate_merge.py watch-check    (reads only: the price watches whose price is now at or below buy-below)
merge (no mode): writes <run>/gate/decisions.csv from each batch's latest file (bNN_rc2 > bNN_rc1 > bNN).
  Columns: sym, decision (NEXT, REJECT or WATCH), batch, stage (rcN or gate), est_cagr, years (the gate entry's years
  field; blank when absent), floor_failed, why, buy_below, eps_basis, waiting_for (blank when absent). Prints the
  NEXT/REJECT/WATCH counts (and any other decision) and the batches not yet rechecked.
  For each WATCH entry writes runs/companies/<SYM>/<run quarter>/watch.json: {sym, name (gate/<SYM>.json, else
  triage.csv), sector (the entry's `sector` when a recheck set it, else gate/<SYM>.json's), kind "price", status
  "watch", analysed_on (today), results_used (the run quarter), buy_below, eps_basis, price_at_gate (triage.csv price),
  watch {waiting_for, evidence_so_far (the entry's why), next_check "", due ""}, note "analysis pending", source
  "gate bNN[_rcN]"} (it replaces a theme watch.json there, printed). A company whose latest decision is no longer
  WATCH loses its price watch.json in the run quarter folder (deleted, printed). Each file written or deleted is
  printed.
watch-check: for every price watch.json in runs/companies/*/<run quarter>/: the current price and P/E (key_ratios
  "Stock P/E") from data/companies/<SYM>/scr/overview.json; EPS now = price / P/E when P/E > 0; buy-below now =
  buy_below x EPS now / eps_basis (when both are known, else buy_below). Prints "REGATE <sym>: price X <= buy-below Y
  (EPS now Z vs W at gate)" for each company at or below its buy-below now, a count line for the rest, and flags an
  overview.json older than 14 days or missing (run scr_company.py --only overview). Writes nothing; exit 0.
"""
import csv, datetime as dt, glob, json, os, re, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_lib as W
from config import analysis_dir, company_runs_dir, run_dir

FIELDS = ['sym', 'decision', 'batch', 'stage', 'est_cagr', 'years', 'floor_failed', 'why', 'buy_below', 'eps_basis',
          'waiting_for']


def run_quarter(run):
    return re.sub(r'_full$', '', os.path.basename(os.path.normpath(run)))


def watch_path(sym, rq):
    return os.path.join(analysis_dir(sym, rq), 'watch.json')


def read_kind(path):
    try:
        return (W.read_json(path) or {}).get('kind')
    except (OSError, ValueError):
        return None


def price_watch(e, src, rq, gate_dir, tri, today):
    """The watch.json of one WATCH entry (src: its file's name, e.g. b09_rc1)."""
    sym = e['sym']
    try:
        g = W.read_json(os.path.join(gate_dir, f'{sym}.json')) or {}
    except (OSError, ValueError):
        g = {}
    w = e.get('watch') if isinstance(e.get('watch'), dict) else {}
    return {'sym': sym, 'name': g.get('name') or (tri.get(sym) or {}).get('name') or '',
            'sector': e.get('sector') or g.get('sector') or '', 'kind': 'price', 'status': 'watch',
            'analysed_on': today, 'results_used': rq, 'buy_below': W.fnum(e.get('buy_below')),
            'eps_basis': W.fnum(e.get('eps_basis')), 'price_at_gate': W.fnum((tri.get(sym) or {}).get('price')),
            'watch': {'waiting_for': e.get('waiting_for') or w.get('waiting_for') or '', 'evidence_so_far': e.get('why') or '',
                      'next_check': '', 'due': ''},
            'note': 'analysis pending', 'source': f'gate {src}'}


def merge():
    run = run_dir()
    g, rq, today = os.path.join(run, 'gate'), run_quarter(run), dt.date.today().isoformat()
    latest = {}
    for fn in glob.glob(os.path.join(g, 'b[0-9]*.json')):
        m = re.match(r'b(\d+)(?:_rc(\d+))?\.json$', os.path.basename(fn))
        if m:
            b, rc = int(m.group(1)), int(m.group(2) or 0)
            if b not in latest or rc > latest[b][0]:
                latest[b] = (rc, fn)
    rows, watches = [], []
    for b, (rc, fn) in sorted(latest.items()):
        d = json.load(open(fn, encoding='utf-8'))
        for e in (d['entries'] if isinstance(d, dict) else d):
            rows.append({'sym': e['sym'], 'decision': e['decision'], 'batch': b, 'stage': f'rc{rc}' if rc else 'gate',
                         'est_cagr': e.get('est_cagr'), 'years': e.get('years'), 'floor_failed': e.get('floor_failed'),
                         'why': e.get('why'), 'buy_below': e.get('buy_below'), 'eps_basis': e.get('eps_basis'),
                         'waiting_for': e.get('waiting_for')})
            if e['decision'] == 'WATCH':
                watches.append((e, os.path.basename(fn)[:-5]))
    with open(os.path.join(g, 'decisions.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    # price watches: written for WATCH entries, removed for companies whose latest decision is no longer WATCH
    tp = os.path.join(run, 'triage.csv')
    tri = {r['sym']: r for r in W.read_csv(tp)} if os.path.exists(tp) else {}
    for e, src in watches:
        p = watch_path(e['sym'], rq)
        k = read_kind(p) if os.path.exists(p) else None
        W.write_json(p, price_watch(e, src, rq, g, tri, today))
        print(f'wrote {p}' + (f' (replaced a {k} watch)' if k and k != 'price' else ''))
    wsyms = {e['sym'] for e, _ in watches}
    for sym in sorted({r['sym'] for r in rows} - wsyms):
        p = watch_path(sym, rq)
        if os.path.exists(p) and read_kind(p) == 'price':
            os.remove(p)
            print(f'deleted {p} (latest decision no longer WATCH)')
    unrechecked = [b for b, (rc, _) in latest.items() if rc == 0]
    other = sorted({r['decision'] for r in rows} - {'NEXT', 'REJECT', 'WATCH'})
    print('decisions', len(rows), 'NEXT', sum(r['decision'] == 'NEXT' for r in rows), 'REJECT', sum(r['decision'] == 'REJECT' for r in rows),
          'WATCH', len(watches), *(['| OTHER DECISIONS:', other] if other else []),
          '| batches not yet rechecked:', unrechecked or 'none')
    return 0


def watch_check():
    run = run_dir()
    rq = run_quarter(run)
    files = sorted(glob.glob(os.path.join(company_runs_dir(), '*', rq, 'watch.json')))
    rest, hits, n = [], [], 0
    for fn in files:
        try:
            w = W.read_json(fn) or {}
        except ValueError:
            print(f'FLAG {fn}: not JSON')
            continue
        if w.get('kind') != 'price':
            continue
        n += 1
        sym = w.get('sym') or os.path.basename(os.path.dirname(os.path.dirname(fn)))
        try:
            env = W.read_json(W.scr_path(sym, 'overview'))
        except (OSError, ValueError):
            print(f'FLAG {sym}: no readable scr/overview.json (run scr_company.py --only overview)')
            continue
        o = env.get('data') or {}
        try:
            age = (dt.date.today() - dt.date.fromisoformat(str(env.get('fetched_at') or '')[:10])).days
        except ValueError:
            age = None
        if age is None or age > 14:
            print(f'FLAG {sym}: overview.json is {"of unknown age" if age is None else f"{age} days old"} (run scr_company.py --only overview)')
        price, pe = W.fnum(o.get('current_price')), W.fnum((o.get('key_ratios') or {}).get('Stock P/E'))
        eps_now = price / pe if price is not None and pe and pe > 0 else None
        bb, basis = W.fnum(w.get('buy_below')), W.fnum(w.get('eps_basis'))
        bb_now = bb * eps_now / basis if bb is not None and eps_now is not None and basis else bb
        f = lambda x: '-' if x is None else f'{x:,.2f}'
        if price is not None and bb_now is not None and price <= bb_now:
            hits.append(f'REGATE {sym}: price {f(price)} <= buy-below {f(bb_now)} (EPS now {f(eps_now)} vs {f(basis)} at gate)')
        else:
            rest.append(sym)
    for h in hits:
        print(h)
    print(f'{n} price watches in {rq}: {len(hits)} to re-gate, {len(rest)} still above buy-below or without a price')
    return 0


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode not in ('', 'watch-check'):
        W.fail(f'unknown mode {mode!r}: none (merge) or watch-check (see --help)')
    sys.exit(watch_check() if mode == 'watch-check' else merge())
