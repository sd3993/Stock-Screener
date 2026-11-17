"""Everything computed per sector, from saved files only (no network, no model): S4 sector numbers, S5 sector order and
sector calls. One subcommand each:
  python -I scripts/sectors.py syms --out FILE [--stage-only] [--sectors FILE] [--history FILE]   (S4)    
  python -I scripts/sectors.py clusters                                                          (S4)    
  python -I scripts/sectors.py stage [--sectors FILE] [--stage-only]                             (S4)      
  python -I scripts/sectors.py order [--from-gate]                                               (S5, S6R)
  python -I scripts/sectors.py log | score [--out FILE]                                          (S5: sector calls)
Each part's inputs, outputs and rules follow in its section below.

---- S4 (workflow/s4_sector_numbers.md) ----
Inputs: the run folder (config.py): universe.csv (S2), triage.csv (S3; queued = triage "gate"), holdings.csv (S1; else
  data/kite/holdings.csv); data/companies/<SYM>/scr/: overview.json (industry label = last element of `sectors`),
  history.json (chart price and P/E), shareholding.json, announcements.json.
syms: queued companies and holdings without overview.json, or without a shareholding.json whose newest quarter is the
  run quarter (one symbol per line, for scr_company.py --only overview,shareholding). --stage-only (recheck): instead the
  members of the sectors in <run>/sectors.json whose overview.json is older than 14 days (their current price and P/E
  come from it). --history FILE also writes the universe companies (or members) without history.json as a CSV with a
  sym column, for mb_history.py --csv.
clusters -> <run>/sector_clusters.csv: per industry label over the universe: n_univ, n_queued, share_q = n_queued/Q,
  share_u = n_univ/U, over = share_q/share_u, binomial z = (n_queued - Q p)/sqrt(Q p (1-p)), p = n_univ/U (blank when
  p is 0 or 1), the holdings in it (a holding outside universe.csv is listed and flagged), queued symbols; companies
  without a label under "(no label)"; sorted by z, highest first.
stage -> <run>/sector_stage.csv: per industry label with 5+ universe companies (full mode), and per sector of
  --sectors (industries plus overrides; a company overridden into a sector counts only there):
  pe_now = median current P/E over members with P/E > 0 (full: universe.csv "Price to Earning"; --stage-only: each
    member's overview.json "Stock P/E", which syms --stage-only keeps fresh);
  pe_pct = percentile of pe_now among pe_hist, the label's median chart P/E (history.json "Price to Earning", last
    weekly point on or before each of the last 40 quarter-ends, > 0, 3+ companies with a value) (needs 20+ quarter-ends);
  ret_1y = median 1-year price return (current price, as for pe_now, against the chart price 52 weeks before its date)
    minus the median over the whole universe (--stage-only: over the members of every sector);
  inst_chg_4q = median (FIIs + DIIs) newest - 4 quarters earlier over members whose shareholding.json has 5+ quarters
    and a newest quarter no more than one quarter before the run quarter; inst_cov = those / members;
  listings_24m = members whose first chart price is within 24 months (members without history.json: unknown, listing_cov);
  issues_12m = members with an announcement in the last 12 months matching QIP|qualified institution|preferential|
    private placement (issue_cov = members with announcements.json);
  stage_suggested, first that applies: crowded if pe_pct >= 80 and (ret_1y in the top fifth of labels, or
    listings_24m + issues_12m >= max(3, 10% of members), or inst_chg_4q in the top fifth of labels); undiscovered if
    pe_pct <= 30 and ret_1y <= 0 and inst_chg_4q <= 0 (or blank) and listings_24m <= 1; early if pe_pct <= 60 and
    (ret_1y > 0 or inst_chg_4q > 0); else recognised; pe_pct blank -> unknown, with the reason.
  It describes how priced-in a sector is (sizing, the re-rating case); tested on past March starts, it did not
  predict later winner rates, so it is not a signal for picking sectors.

---- order (S5 after S5R; S6R with --from-gate) ----
Maps every queued company and holding to a sector of the map, queues the emerging entries' companies, and reorders the
gate batches not yet run, tailwind sectors first.
Inputs (run folder, config.py): sectors.json (S5: id, rank, industries, overrides, emerging), triage.csv (queued =
  triage "gate"; name, headroom, triage, reason), holdings.csv (S1; else data/kite/holdings.csv), gate_batches.json
  (S3), gate/bNN.json (batches already run), with --from-gate gate/<SYM>.json (the gate's confirmed `sector`); industry
  labels from data/companies/<SYM>/scr/overview.json.
Sector of a company: an `overrides` entry first, an emerging entry before the others (source emerging, else override;
  several entries overriding the same company: the lower rank number among those, listed as ambiguous), else the
  sector whose `industries` holds its label (two sectors: the lower rank number wins, ambiguous), else "other" (rank =
  highest + 1); --from-gate: the gate file's sector wins (source gate). A gate sector that is neither in sectors.json
  nor "other" stops the script (listed), writing nothing.
Emerging names: every `overrides` company of an entry with "emerging": true joins the queue even when triage did not
  queue it (triage not_queued, including no positive P/E, or a return-math reject). Not added: a holding; a company in
  a batch that has run; a company triage rejected for anything but return math (REIT/InvIT, promoter pledge, cash
  conversion), which is also taken out of a pending batch it sits in. A company absent from triage.csv is added (no
  headroom: last within its sector). Printed: the emerging names added, those absent from triage.csv, and those
  blocked, each with the reason. Overrides of an entry not marked emerging add no company to the queue: they only map
  companies queued or held.
Outputs: sector_of.tsv (sym, name, held, industry, sector, rank, source: override/emerging/label/gate/other, ambiguous)
  for every holding, queued company and emerging name added; gate_batches.json rebuilt: batches already run (a
  gate/bNN.json exists) keep their number and content; every other queued company and emerging name added (holdings
  never) goes into batches of 10 ordered by sector rank, then triage headroom (highest first), numbered after the last
  run batch; the old file is kept as gate_batches_<YYYYmmdd_HHMMSS>.json when it changes.
  Safe to re-run: nothing changes when nothing changed.

---- log, score (S5: sector calls) ----
log: for each sector in <run>/sectors.json whose call differs from its last logged row in runs/sector_calls.csv (kind,
  emerging, stage, start, end, capture, industries, and each marker's id, op, threshold, event and due), or that has no
  row yet, appends: call_id (<sector id>-<call_date>), date, run, sector, name, kind, emerging (true/false), stage, start,
  end, capture, rank, industries, overrides, markers (JSON), members (JSON: the universe companies in the sector at the call, as
  stage counts them, for the later return), supersedes (the sector's previous call_id), note ("possible rename
  of <old id>" when a new id has the same industries as a logged id missing from the map). An unchanged call is not
  logged again, so re-running is safe. Each marker state in sectors.json (state, state_date, state_evidence) is appended
  once to runs/sector_marker_states.csv (call_id, marker, date, state, evidence).
score: every logged call 6+ months old: its markers held / broken / pending (due date not reached) / unchecked (due
  passed, no state recorded), from sector_marker_states.csv across the sector's later calls; the median price return of
  its members since the call date against the median of the universe (universe.csv of the call's run, else this run's)
  over the same period, at 6, 12 and 24 months where reached (chart prices, history.json); blank with the reason when
  no member has prices. Whether the stage proved right is not judged here. Summary: calls scored, share with every due
  marker held, median excess return of tailwind calls against "none" calls, by stage. Writes <run>/sector_calls_score.md.
"""
import argparse, bisect, datetime as dt, glob, json, math, os, re, statistics as st, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_lib as W
from config import run_dir, run_path, shared_path

MIN_LABEL, MIN_AT_DATE, MIN_QE, QE_YEARS = 5, 3, 20, 10
ISSUE_RE = re.compile(r'QIP|qualified institution|preferential|private placement', re.I)
CROWD_PCT, UND_PCT, EARLY_PCT = 80, 30, 60
NO_LABEL = '(no label)'


def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def r2(x, n=2):
    return None if x is None else round(x, n)


def run_quarter(run):
    return re.sub(r'_full$', '', os.path.basename(os.path.normpath(run)))


def holdings(run):
    p = os.path.join(run, 'holdings.csv')
    if not os.path.exists(p):
        p = os.path.join('data', 'kite', 'holdings.csv')
        print(f'note: no {os.path.join(run, "holdings.csv")}; holdings from {p}')
    return W.holdings_syms(p)


def universe(run, need=True):
    p = os.path.join(run, 'universe.csv')
    if not os.path.exists(p):
        if need:
            W.fail(f'{p} missing: run S2 (screens.py build) first')
        return None
    return {r['sym']: r for r in W.read_csv(p)}


def queued(run):
    p = os.path.join(run, 'triage.csv')
    if not os.path.exists(p):
        W.fail(f'{p} missing: run S3 (triage.py) first')
    return [r['sym'] for r in W.read_csv(p) if r.get('triage') == 'gate']


def shp_newest(sym):
    d = W.scr(sym, 'shareholding')
    q = (d or {}).get('quarters') or []
    try:
        return W.fyq_of_label(q[-1]) if q else None
    except (KeyError, ValueError, IndexError):
        return None


def age_days(sym, name):
    try:
        t = W.read_json(W.scr_path(sym, name)).get('fetched_at', '')[:10]
        return (dt.date.today() - dt.date.fromisoformat(t)).days
    except (OSError, ValueError, AttributeError):
        return None


# ---------- sectors ----------
def load_sectors(path):
    if not os.path.exists(path):
        W.fail(f'{path} missing')
    try:
        return W.read_json(path).get('sectors') or []
    except ValueError as e:
        W.fail(f'{path}: not JSON ({e})')


def sector_members(sectors, pool):
    """{sector id: [syms]}: pool companies whose label is in the sector's industries, plus overrides; a company overridden
    into a sector counts only there (in two sectors' overrides: the first by rank, warned)."""
    over, warn = {}, []
    for s in sorted(sectors, key=lambda s: s.get('rank') or 999):
        for sym in (s.get('overrides') or {}):
            if sym in over and over[sym] != s['id']:
                warn.append(f'{sym} in overrides of {over[sym]} and {s["id"]}: counted in {over[sym]}')
                continue
            over[sym] = s['id']
    out = {s['id']: [] for s in sectors}
    for sym in sorted(set(pool) | set(over)):
        if sym in over:
            out[over[sym]].append(sym)
            continue
        lab = W.industry(sym)
        for s in sorted(sectors, key=lambda s: s.get('rank') or 999):
            if lab and lab in (s.get('industries') or []):
                out[s['id']].append(sym)
                break
    for w in warn:
        print('WARNING', w)
    return out


# ---------- syms ----------
def cmd_syms(a):
    run = run_dir()
    if a.stage_only:
        sp = a.sectors or os.path.join(run, 'sectors.json')
        u = universe(run, need=False) or last_full_universe(run)
        mem = sector_members(load_sectors(sp), u)
        allm = sorted({s for v in mem.values() for s in v})
        todo = [s for s in allm if (age_days(s, 'overview') or 999) > 14]
        hist_pool = allm
        what = f'{len(allm)} sector members, {len(todo)} with no overview.json or one older than 14 days'
    else:
        q, hs, rq = queued(run), holdings(run), run_quarter(run)
        pool = list(dict.fromkeys(q + hs))
        def needs(s):
            n = shp_newest(s)
            return not os.path.exists(W.scr_path(s, 'overview')) or n is None or W.fyq_index(n) < W.fyq_index(rq)
        todo = [s for s in pool if needs(s)]
        hist_pool = sorted(set(universe(run)) | set(pool))
        what = (f'{len(pool)} queued and holdings, {len(todo)} without overview.json or a {rq} shareholding.json '
                f'({sum(not os.path.exists(W.scr_path(s, "overview")) for s in pool)} without overview)')
    W.write_text(a.out, ''.join(s + '\n' for s in todo))
    print(f'{what} -> {a.out}')
    if a.history:
        nh = [s for s in hist_pool if not os.path.exists(W.scr_path(s, 'history'))]
        W.write_text(a.history, 'sym\n' + ''.join(s + '\n' for s in nh))  # a CSV for mb_history.py --csv
        print(f'{len(nh)} of {len(hist_pool)} without history.json -> {a.history}')
    return 0


def last_full_universe(run):
    """Recheck mode: universe.csv of the run the sector map came from (progress.md "Sector map from: <run>")."""
    try:
        txt = open(os.path.join(run, 'progress.md'), encoding='utf-8').read()
    except OSError:
        txt = ''
    m = re.search(r'^Sector map from: (\S+)', txt, re.M)
    src = m.group(1) if m else None
    u = universe(src, need=False) if src else None
    if u is None:
        W.fail(f'no universe.csv in this run or in the run the sector map came from ({src}): run S2 or check progress.md')
    return u


# ---------- clusters ----------
def cmd_clusters(a):
    run = run_dir()
    u, q, hs = universe(run), queued(run), holdings(run)
    Q, U = len(q), len(u)
    if not U:
        W.fail('universe.csv has no companies')
    lab = lambda s: W.industry(s) or NO_LABEL
    nu, nq, hl, qs = Counter(lab(s) for s in u), Counter(lab(s) for s in q), defaultdict(list), defaultdict(list)
    outside = [s for s in hs if s not in u]
    for s in hs:
        hl[lab(s)].append(s + ('*' if s in outside else ''))
    for s in q:
        qs[lab(s)].append(s)
    rows = []
    for L in sorted(set(nu) | set(nq) | set(hl)):
        p = nu[L] / U
        var = Q * p * (1 - p)
        rows.append({'label': L, 'n_univ': nu[L], 'n_queued': nq[L], 'share_q': r2(nq[L] / Q, 4) if Q else None,
                     'share_u': r2(p, 4), 'over': r2((nq[L] / Q) / p, 2) if Q and p else None,
                     'z': r2((nq[L] - Q * p) / math.sqrt(var), 2) if var > 0 else None,
                     'holdings': ' '.join(hl[L]), 'queued': ' '.join(qs[L])})
    rows.sort(key=lambda r: (r['z'] is None, -(r['z'] or 0), r['label']))
    out = os.path.join(run, 'sector_clusters.csv')
    W.write_csv(out, ['label', 'n_univ', 'n_queued', 'share_q', 'share_u', 'over', 'z', 'holdings', 'queued'], rows)
    nol = [s for s in u if not W.industry(s)]
    print(f'{len(rows)} labels, universe {U}, queued {Q}, holdings {len(hs)} ({len(outside)} outside the universe, '
          f'flagged *: {outside}); without a label: {len(nol)} universe, {nq[NO_LABEL]} queued -> {out}')
    return 0


# ---------- stage ----------
class Hist:
    """Chart series of one company: price and P/E (history.json), as (date, value) lists."""
    _c = {}

    @classmethod
    def get(cls, sym):
        if sym not in cls._c:
            h = W.scr(sym, 'history')
            if h is None:
                cls._c[sym] = None
            else:
                ds = lambda k, n: W.series(((h.get(k) or {}).get('datasets') or {}).get(n))
                px, pe = ds('price', 'Price'), ds('pe', 'Price to Earning')
                cls._c[sym] = {'px': px, 'pxd': [t for t, _ in px], 'pe': pe, 'ped': [t for t, _ in pe]}
        return cls._c[sym]


def at(dates, pts, d, gap=21):
    i = bisect.bisect_right(dates, d) - 1
    return pts[i][1] if i >= 0 and (d - pts[i][0]).days <= gap else None


def quarter_ends(today, n):
    """The last n quarter-ends on or before today, oldest first."""
    out, e = [], W.fyq_end(W.fyq_of(today))
    if e > today:
        e = W.fyq_end(prev_q(W.fyq_of(today)))
    while len(out) < n:
        out.append(e)
        e = W.fyq_end(prev_q(W.fyq_of(e)))
    return sorted(out)


def prev_q(q):
    i = W.fyq_index(q) - 1
    return f'FY{(i - 1) // 4:02d}Q{(i - 1) % 4 + 1}'


def now_values(syms, u, use_overview):
    """{sym: (pe, price, date)} from universe.csv (full) or overview.json (--stage-only)."""
    out = {}
    if not use_overview:
        d = dt.date.fromtimestamp(os.path.getmtime(os.path.join(run_dir(), 'universe.csv')))
        for s in syms:
            r = u.get(s) or {}
            out[s] = (W.fnum(r.get('Price to Earning')), W.fnum(r.get('Current Price')), d)
        return out
    for s in syms:
        try:
            env = W.read_json(W.scr_path(s, 'overview'))
            o = env.get('data') or {}
            out[s] = (W.fnum((o.get('key_ratios') or {}).get('Stock P/E')), W.fnum(o.get('current_price')),
                      dt.date.fromisoformat(env.get('fetched_at', '')[:10]))
        except (OSError, ValueError, AttributeError):
            out[s] = (None, None, None)
    return out


def ret1(sym, price, d):
    h = Hist.get(sym)
    if not h or price is None or d is None or price <= 0:
        return None
    p0 = at(h['pxd'], h['px'], d - dt.timedelta(weeks=52), gap=21)
    return (price / p0 - 1) * 100 if p0 and p0 > 0 else None


def inst_chg(sym, rq):
    d = W.scr(sym, 'shareholding')
    rows, qs = W.table(d)
    if len(qs) < 5:
        return None
    try:
        if W.fyq_index(rq) - W.fyq_index(W.fyq_of_label(qs[-1])) > 1:
            return None  # stale
    except (KeyError, ValueError):
        return None
    def tot(i):  # a row screener leaves out counts as 0; a row with a blank at that quarter makes it unknown
        s, seen = 0.0, False
        for k in ('FIIs', 'DIIs'):
            v = rows.get(k)
            if not v:
                continue
            if len(v) < -i or v[i] is None:
                return None
            s, seen = s + v[i], True
        return s if seen else None
    n, o = tot(-1), tot(-5)
    return n - o if n is not None and o is not None else None


def listed_recently(sym, d):
    h = Hist.get(sym)
    if not h or not h['px']:
        return None
    return (d - h['px'][0][0]).days <= 730


def issued_recently(sym, d):
    a = W.scr(sym, 'announcements')
    if a is None or a.get('nse_listed') is False:
        return None
    for x in a.get('announcements') or []:
        try:
            t = dt.datetime.strptime(x.get('date', '')[:11], '%d-%b-%Y').date()
        except ValueError:
            continue
        if 0 <= (d - t).days <= 365 and ISSUE_RE.search(' '.join(str(x.get(k) or '') for k in ('headline', 'category', 'nse_category'))):
            return True
    return False


def suggest(pe_pct, ret, ret_top, inst, inst_top, listings, issues, n):
    """The fixed rule; returns (stage, reason)."""
    if pe_pct is None:
        return 'unknown', 'no P/E percentile (fewer than 20 quarter-ends of history, or no current P/E > 0)'
    supply = (listings or 0) + (issues or 0)
    if pe_pct >= CROWD_PCT:
        why = [x for x, ok in (('1y return in the top fifth', ret is not None and ret_top is not None and ret >= ret_top),
                               (f'{supply} listings + issues', supply >= max(3, 0.1 * n)),
                               ('institutional buying in the top fifth', inst is not None and inst_top is not None and inst >= inst_top)) if ok]
        if why:
            return 'crowded', f'P/E at the {pe_pct:.0f}th percentile of its history; ' + ', '.join(why)
    if pe_pct <= UND_PCT and ret is not None and ret <= 0 and (inst is None or inst <= 0) and (listings or 0) <= 1:
        return 'undiscovered', f'P/E at the {pe_pct:.0f}th percentile, 1y return {ret:+.0f} vs universe, no institutional buying'
    if pe_pct <= EARLY_PCT and ((ret is not None and ret > 0) or (inst is not None and inst > 0)):
        return 'early', f'P/E at the {pe_pct:.0f}th percentile with ' + ('price strength' if ret is not None and ret > 0 else 'institutional buying')
    return 'recognised', f'P/E at the {pe_pct:.0f}th percentile'


def pct_rank(x, hist):
    return (sum(h < x for h in hist) + 0.5 * sum(h == x for h in hist)) / len(hist) * 100


def top_fifth(vals):
    v = sorted(x for x in vals if x is not None)
    return v[int(len(v) * 0.8)] if len(v) >= 5 else None


def group_numbers(name, kind, syms, nowv, qes, rq, today, ret_base):
    pes = [nowv[s][0] for s in syms if nowv.get(s, (None,))[0] and nowv[s][0] > 0]
    pe_now = med(pes)
    hist = []
    for qe in qes:
        v = []
        for s in syms:
            h = Hist.get(s)
            if h:
                p = at(h['ped'], h['pe'], qe, gap=21)
                if p is not None and p > 0:
                    v.append(p)
        if len(v) >= MIN_AT_DATE:
            hist.append(st.median(v))
    rets = [ret1(s, nowv[s][1], nowv[s][2]) for s in syms if s in nowv]
    rets = [x for x in rets if x is not None]
    insts = [x for x in (inst_chg(s, rq) for s in syms) if x is not None]
    lst = [listed_recently(s, today) for s in syms]
    iss = [issued_recently(s, today) for s in syms]
    return {'kind': kind, 'id': name, 'n': len(syms), 'pe_now': r2(pe_now, 1), 'pe_now_n': len(pes),
            'pe_hist_q': len(hist), 'pe_hist_med': r2(med(hist), 1),
            'pe_pct': r2(pct_rank(pe_now, hist), 0) if pe_now and len(hist) >= MIN_QE else None,
            'ret_1y': r2(med(rets) - ret_base, 1) if rets and ret_base is not None else None, 'ret_n': len(rets),
            'inst_chg_4q': r2(med(insts), 2), 'inst_cov': r2(len(insts) / len(syms), 2) if syms else None,
            'listings_24m': sum(1 for x in lst if x), 'listing_cov': r2(sum(x is not None for x in lst) / len(syms), 2) if syms else None,
            'issues_12m': sum(1 for x in iss if x), 'issue_cov': r2(sum(x is not None for x in iss) / len(syms), 2) if syms else None}


def cmd_stage(a):
    run = run_dir()
    rq, today = run_quarter(run), dt.date.today()
    if a.stage_only and not a.sectors:
        W.fail('--stage-only needs --sectors <run>/sectors.json')
    u = universe(run, need=not a.stage_only) or (last_full_universe(run) if a.stage_only else None)
    sectors = load_sectors(a.sectors) if a.sectors else []
    mem = sector_members(sectors, u) if sectors else {}
    groups = []
    if not a.stage_only:
        by = defaultdict(list)
        for s in u:
            if W.industry(s):
                by[W.industry(s)].append(s)
        groups += [('label', L, v) for L, v in sorted(by.items()) if len(v) >= MIN_LABEL]
    groups += [('sector', sid, v) for sid, v in mem.items()]
    pool = sorted(u) if not a.stage_only else sorted({s for v in mem.values() for s in v})
    nowv = now_values(sorted(set(pool) | {s for _, _, v in groups for s in v}), u, a.stage_only)
    base = med([ret1(s, nowv[s][1], nowv[s][2]) for s in pool])
    qes = quarter_ends(today, QE_YEARS * 4)
    rows = [group_numbers(n, k, v, nowv, qes, rq, today, base) for k, n, v in groups]
    labs = [r for r in rows if r['kind'] == 'label'] or rows
    rt, it = top_fifth([r['ret_1y'] for r in labs]), top_fifth([r['inst_chg_4q'] for r in labs])
    for r in rows:
        r['stage_suggested'], r['reason'] = suggest(r['pe_pct'], r['ret_1y'], rt, r['inst_chg_4q'], it,
                                                    r['listings_24m'], r['issues_12m'], r['n'])
    fields = ['kind', 'id', 'n', 'pe_now', 'pe_now_n', 'pe_hist_q', 'pe_hist_med', 'pe_pct', 'ret_1y', 'ret_n', 'inst_chg_4q',
              'inst_cov', 'listings_24m', 'listing_cov', 'issues_12m', 'issue_cov', 'stage_suggested', 'reason']
    out = os.path.join(run, 'sector_stage.csv')
    W.write_csv(out, fields, rows)
    c = Counter(r['stage_suggested'] for r in rows)
    print(f'{sum(r["kind"] == "label" for r in rows)} labels, {sum(r["kind"] == "sector" for r in rows)} sectors; '
          f'universe median 1y return {r2(base, 1)}%; top fifth: ret {rt}, inst {it}; stages {dict(c)} -> {out}')
    return 0


# ---------- order (S5, S6R) ----------
BATCH = 10  # gate batch size
OF_FIELDS = ['sym', 'name', 'held', 'industry', 'sector', 'rank', 'source', 'ambiguous']


def load_map(run):
    p = os.path.join(run, 'sectors.json')
    if not os.path.exists(p):
        W.fail(f'{p} missing: S5 writes it first')
    try:
        secs = W.read_json(p).get('sectors') or []
    except ValueError as e:
        W.fail(f'{p}: not JSON ({e})')
    bad = [s.get('id') for s in secs if not s.get('id') or not isinstance(s.get('rank'), (int, float))]
    if bad:
        W.fail(f'{p}: sectors without an id or a numeric rank: {bad}')
    return sorted(secs, key=lambda s: s['rank'])


def emerging(s):
    """Whether a sectors.json entry is marked emerging ("emerging": true)."""
    return s.get('emerging') is True


def blocking_reject(r):
    """The triage reject that keeps an emerging name out of the queue (REIT/InvIT, pledge, cash conversion), or None.
    A return-math reject (math dead) does not block: an emerging name's growth is not in its trailing figures."""
    if (r or {}).get('triage') != 'reject' or (r.get('math') == 'dead' and r.get('reason', '').startswith('return math')):
        return None
    return r.get('reason') or 'triage reject'


def assign(sym, secs, other_rank, gate_sector=None):
    """(sector, rank, source, ambiguous)."""
    by_id = {s['id']: s for s in secs}
    if gate_sector:
        return gate_sector, by_id[gate_sector]['rank'] if gate_sector in by_id else other_rank, 'gate', ''
    ov = [s for s in secs if sym in (s.get('overrides') or {})]
    ov.sort(key=lambda s: not emerging(s))  # stable: an emerging entry first, then by rank
    if ov:
        return (ov[0]['id'], ov[0]['rank'], 'emerging' if emerging(ov[0]) else 'override',
                ' '.join(s['id'] for s in ov) if len(ov) > 1 else '')
    lab = W.industry(sym)
    hit = [s for s in secs if lab and lab in (s.get('industries') or [])]
    if hit:
        return hit[0]['id'], hit[0]['rank'], 'label', ' '.join(s['id'] for s in hit) if len(hit) > 1 else ''
    return 'other', other_rank, 'other', ''


def cmd_order(a):
    run = run_dir()
    secs = load_map(run)
    other_rank = max([s['rank'] for s in secs] + [0]) + 1
    tp = os.path.join(run, 'triage.csv')
    if not os.path.exists(tp):
        W.fail(f'{tp} missing: run S3 first')
    tri = {r['sym']: r for r in W.read_csv(tp)}
    hp = os.path.join(run, 'holdings.csv')
    held = W.holdings_syms(hp if os.path.exists(hp) else os.path.join('data', 'kite', 'holdings.csv'))
    queued = [s for s, r in tri.items() if r.get('triage') == 'gate']
    gate_sec, unknown = {}, []
    if a.from_gate:
        ids = {s['id'] for s in secs} | {'other'}
        for fn in glob.glob(os.path.join(run, 'gate', '*.json')):
            sym = os.path.basename(fn)[:-5]
            if re.match(r'b\d+(_rc\d+)?$', sym) or sym == 'decisions':
                continue
            try:
                sec = (W.read_json(fn) or {}).get('sector')
            except ValueError:
                W.fail(f'{fn}: not JSON')
            if sec:
                gate_sec[sym] = sec
                if sec not in ids:
                    unknown.append(f'{sym}: {sec}')
        if unknown:
            W.fail(f'gate files name sectors not in sectors.json: {unknown} (fix the gate file or add the sector)')
    # batches already run
    bp = os.path.join(run, 'gate_batches.json')
    old = W.read_json(bp) if os.path.exists(bp) else {'batches': {}}
    ran = set()
    for fn in glob.glob(os.path.join(run, 'gate', 'b*.json')):
        m = re.match(r'b(\d+)(?:_rc\d+)?\.json$', os.path.basename(fn))
        if m:
            ran.add(int(m.group(1)))
    keep = {k: v for k, v in old['batches'].items() if int(k) in ran}
    done = {s for v in keep.values() for s in v}
    # emerging names: every override of an emerging entry, unless held, already gated or hard-rejected by triage
    em_add, em_absent, em_blocked = [], [], []
    for sec in secs:
        if not emerging(sec):
            continue
        for sym in sec.get('overrides') or {}:
            if sym in em_add or any(sym == b[0] for b in em_blocked):
                continue
            why = ('held' if sym in held else 'in a batch that has run' if sym in done
                   else blocking_reject(tri[sym]) if sym in tri else None)
            if why:
                em_blocked.append((sym, sec['id'], why))
                continue
            em_add.append(sym)
            if sym not in tri:
                em_absent.append(sym)
    em_new = [s for s in em_add if s not in queued]  # added beyond triage's queue
    hard = {s for s, _, why in em_blocked if why not in ('held', 'in a batch that has run')}
    rows = []
    for sym in list(dict.fromkeys(held + queued + em_new)):
        sec, rank, src, amb = assign(sym, secs, other_rank, gate_sec.get(sym))
        rows.append({'sym': sym, 'name': (tri.get(sym) or {}).get('name', ''), 'held': sym in held,
                     'industry': W.industry(sym) or '', 'sector': sec, 'rank': rank, 'source': src, 'ambiguous': amb})
    rows.sort(key=lambda r: (not r['held'], r['rank'], r['sym']))
    W.write_csv(os.path.join(run, 'sector_of.tsv'), OF_FIELDS, rows, delimiter='\t')
    # gate batches
    pending = [s for k, v in sorted(old['batches'].items(), key=lambda x: int(x[0])) if int(k) not in ran for s in v]
    pending += [s for s in queued + em_new if s not in pending]
    pending = [s for s in dict.fromkeys(pending) if s not in done and s not in held and s not in hard]
    info = {r['sym']: r for r in rows}
    head = lambda s: W.fnum((tri.get(s) or {}).get('headroom'))
    pending.sort(key=lambda s: ((info[s]['rank'] if s in info else assign(s, secs, other_rank)[1]),
                                -(head(s) if head(s) is not None else -999), s))
    n = max(list(ran) + [int(k) for k in keep] + [0])
    new = {'batches': dict(sorted(keep.items(), key=lambda x: int(x[0])))}
    for i in range(0, len(pending), BATCH):
        n += 1
        new['batches'][str(n)] = pending[i:i + BATCH]
    changed = new != old
    if changed:
        if os.path.exists(bp):
            os.replace(bp, os.path.join(run, f'gate_batches_{dt.datetime.now():%Y%m%d_%H%M%S}.json'))
        W.write_json(bp, new)
    amb = [r['sym'] for r in rows if r['ambiguous']]
    by = {}
    for r in rows:
        by[r['sector']] = by.get(r['sector'], 0) + 1
    print(f'{len(rows)} companies ({len(held)} holdings) mapped: {by}; ambiguous {amb or "none"}; '
          f'{"from gate " + str(len(gate_sec)) + "; " if a.from_gate else ""}'
          f'gate batches: {len(keep)} run kept, {len(new["batches"]) - len(keep)} rebuilt ({len(pending)} companies)'
          f'{"" if changed else "; unchanged, nothing rewritten"}')
    print(f'emerging names: {len(em_add)} in the queue, {len(em_new)} of them added beyond the triage queue '
          f'({" ".join(em_new) or "none"}); absent from triage.csv: {" ".join(em_absent) or "none"}; blocked: {len(em_blocked)}')
    for s, sid, why in em_blocked:
        print(f'  blocked {s} ({sid}): {why}')
    return 0


# ---------- log, score (S5: sector calls) ----------
CALLS = shared_path('sector_calls.csv')
STATES = shared_path('sector_marker_states.csv')
CALL_FIELDS = ['call_id', 'date', 'run', 'sector', 'name', 'kind', 'emerging', 'stage', 'start', 'end', 'capture', 'rank',
          'industries', 'overrides', 'markers', 'members', 'supersedes', 'note']
SFIELDS = ['call_id', 'marker', 'date', 'state', 'evidence']
MK = ('id', 'op', 'threshold', 'event', 'due')


def sig(kind, em, stage, start, end, capture, industries, markers):
    return json.dumps([kind, em, stage, start, end, capture, sorted(industries or []),
                       sorted([[m.get(k) for k in MK] for m in markers or []], key=lambda x: str(x[0]))], sort_keys=True, default=str)


def row_sig(r):
    return sig(r['kind'], r['emerging'], r['stage'], r['start'], r['end'], r['capture'], json.loads(r['industries'] or '[]'),
               json.loads(r['markers'] or '[]'))


def em_text(s):
    """The logged emerging field: 'true' or 'false'."""
    return 'true' if emerging(s) else 'false'


def sec_sig(s):
    f = lambda k: '' if s.get(k) is None else str(s.get(k))
    return sig(f('kind'), em_text(s), f('stage'), f('start'), f('end'), f('capture'), s.get('industries'),
               [{k: m.get(k) for k in MK} for m in s.get('markers') or []])


def members(run, sectors):
    u = universe(run, need=False)
    if u is None:
        try:
            u = last_full_universe(run)
        except SystemExit:
            u = {}
    return sector_members(sectors, u)


def cmd_log(a):
    run = run_dir()
    p = os.path.join(run, 'sectors.json')
    if not os.path.exists(p):
        W.fail(f'{p} missing')
    secs = W.read_json(p).get('sectors') or []
    if not secs:
        W.fail(f'{p}: no sectors')
    rows = W.read_csv(CALLS) if os.path.exists(CALLS) else []
    last = {}
    for r in rows:
        last[r['sector']] = r
    ids_now = {s['id'] for s in secs}
    mem = members(run, secs)
    new, today = [], dt.date.today().isoformat()
    for s in secs:
        prev = last.get(s['id'])
        if prev and row_sig(prev) == sec_sig(s):
            continue
        date = str(s.get('call_date') or today)
        cid, k = f"{s['id']}-{date}", 2
        while any(r['call_id'] == cid for r in rows + new):
            cid, k = f"{s['id']}-{date}-{k}", k + 1
        note = ''
        if not prev:
            ren = [r['sector'] for r in last.values() if r['sector'] not in ids_now and
                   sorted(json.loads(r['industries'] or '[]')) == sorted(s.get('industries') or [])]
            note = f'possible rename of {", ".join(ren)}' if ren else ''
        new.append({'call_id': cid, 'date': date, 'run': os.path.basename(os.path.normpath(run)), 'sector': s['id'],
                    'name': s.get('name', ''), 'kind': s.get('kind', ''), 'emerging': em_text(s), 'stage': s.get('stage', ''),
                    'start': s.get('start', ''), 'end': s.get('end', ''), 'capture': s.get('capture', ''), 'rank': s.get('rank', ''),
                    'industries': json.dumps(s.get('industries') or [], ensure_ascii=False),
                    'overrides': json.dumps(sorted(s.get('overrides') or {}), ensure_ascii=False),
                    'markers': json.dumps(s.get('markers') or [], ensure_ascii=False),
                    'members': json.dumps(mem.get(s['id'], [])), 'supersedes': prev['call_id'] if prev else '', 'note': note})
        last[s['id']] = new[-1]
    if new:
        W.append_csv(CALLS, CALL_FIELDS, new)
    states = W.read_csv(STATES) if os.path.exists(STATES) else []
    seen = {(r['call_id'], r['marker'], r['date'], r['state']) for r in states}
    add = []
    for s in secs:
        cid = last[s['id']]['call_id']
        for m in s.get('markers') or []:
            if not m.get('state'):
                continue
            key = (cid, str(m.get('id')), str(m.get('state_date') or ''), str(m['state']))
            if key not in seen:
                seen.add(key)
                add.append(dict(zip(SFIELDS, list(key) + [m.get('state_evidence') or ''])))
    if add:
        W.append_csv(STATES, SFIELDS, add)
    print(f'{len(secs)} sectors: {len(new)} calls logged ({", ".join(r["call_id"] + (" [" + r["note"] + "]" if r["note"] else "") for r in new) or "none"}), '
          f'{len(add)} marker states -> {CALLS}, {STATES}')
    return 0


def ret(sym, d0, d1):
    h = Hist.get(sym)
    if not h:
        return None
    p0, p1 = at(h['pxd'], h['px'], d0, 21), at(h['pxd'], h['px'], d1, 21)
    return (p1 / p0 - 1) * 100 if p0 and p1 and p0 > 0 else None


def cmd_score(a):
    run = run_dir()
    if not os.path.exists(CALLS):
        W.fail(f'{CALLS} missing: nothing logged yet (sectors.py log)')
    rows, today = W.read_csv(CALLS), dt.date.today()
    states = W.read_csv(STATES) if os.path.exists(STATES) else []
    chain = {}
    for r in rows:
        chain.setdefault(r['sector'], []).append(r['call_id'])
    univ_cache = {}

    def univ(rn):
        if rn not in univ_cache:
            u = universe(run_path(rn), need=False) or universe(run, need=False) or {}
            univ_cache[rn] = sorted(u)
        return univ_cache[rn]
    out, scored = [], []
    for r in rows:
        d0 = dt.date.fromisoformat(r['date'][:10])
        if (today - d0).days < 182:
            continue
        later = chain[r['sector']][chain[r['sector']].index(r['call_id']):]
        mk = {'held': 0, 'broken': 0, 'pending': 0, 'unchecked': 0}
        for m in json.loads(r['markers'] or '[]'):
            ss = sorted((x for x in states if x['call_id'] in later and x['marker'] == str(m.get('id'))), key=lambda x: x['date'])
            due = m.get('due')
            try:
                due_d = dt.date.fromisoformat(str(due)[:10]) if due else None
            except ValueError:
                due_d = None
            if any(x['state'] == 'broken' for x in ss):
                mk['broken'] += 1
            elif due_d and due_d > today:
                mk['pending'] += 1
            elif ss and ss[-1]['state'] in ('held', 'near'):
                mk['held'] += 1
            else:
                mk['unchecked'] += 1
        mem = json.loads(r['members'] or '[]')
        ex, why = {}, ''
        for mo in (6, 12, 24):
            d1 = W.add_years(d0, mo // 12) if mo % 12 == 0 else d0 + dt.timedelta(days=182)
            if d1 > today:
                continue
            m_r = [x for x in (ret(s, d0, d1) for s in mem) if x is not None]
            u_r = [x for x in (ret(s, d0, d1) for s in univ(r['run'])) if x is not None]
            if not m_r:
                why = f'no member prices ({len(mem)} members)'
                continue
            ex[mo] = (st.median(m_r) - st.median(u_r)) if u_r else None
        scored.append({**r, **mk, 'ex': ex, 'why': why})
    lines = [f'# Sector calls scored ({today}; calls 6+ months old)', '',
             '| call | kind | stage | markers held / broken / pending / unchecked | excess return 6m | 12m | 24m | note |', '|---|---|---|---|---|---|---|---|']
    fmt = lambda x: '-' if x is None else f'{x:+.1f}%'
    for s in scored:
        lines.append(f"| {s['call_id']} | {s['kind']} | {s['stage']} | {s['held']} / {s['broken']} / {s['pending']} / {s['unchecked']} | "
                     f"{fmt(s['ex'].get(6))} | {fmt(s['ex'].get(12))} | {fmt(s['ex'].get(24))} | {s['why'] or s['note']} |")
    due = [s for s in scored if s['held'] + s['broken'] + s['unchecked']]
    allheld = [s for s in due if not s['broken'] and not s['unchecked']]
    lines += ['', f'Calls scored: {len(scored)}; with every due marker held: {len(allheld)} of {len(due)} with markers due.']
    for mo in (12, 6, 24):
        tw = [s['ex'][mo] for s in scored if s['ex'].get(mo) is not None and s['kind'] not in ('none', '')]
        no = [s['ex'][mo] for s in scored if s['ex'].get(mo) is not None and s['kind'] in ('none', '')]
        lines.append(f'{mo} months: median excess return of tailwind calls {fmt(st.median(tw) if tw else None)} ({len(tw)}), '
                     f'of "none" calls {fmt(st.median(no) if no else None)} ({len(no)})')
        for stage in ('undiscovered', 'early', 'recognised', 'crowded'):
            v = [s['ex'][mo] for s in scored if s['stage'] == stage and s['ex'].get(mo) is not None]
            if v:
                lines.append(f'  - {stage}: {fmt(st.median(v))} ({len(v)})')
    path = a.out or os.path.join(run, 'sector_calls_score.md')
    W.write_text(path, '\n'.join(lines) + '\n')
    print(f'{len(rows)} calls logged, {len(scored)} scored -> {path}')
    return 0


def doc_part(head):
    """A mode's --help: the docstring's usage lines plus its '---- <head>' section."""
    parts = __doc__.split('\n---- ')
    return parts[0] + '\n---- ' + next(p for p in parts[1:] if p.startswith(head))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True, help='the mode; <mode> --help for its own help')
    p = sp.add_parser('syms', help='symbols to fetch for S4 (S4)', description=doc_part('S4'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', required=True, help='the symbol list file (required)')
    p.add_argument('--stage-only', action='store_true', help='recheck: members of the sectors with a stale overview.json')
    p.add_argument('--sectors', help='with --stage-only: the sectors file (default: <run>/sectors.json)')
    p.add_argument('--history', metavar='FILE', help='also write companies without history.json as a CSV (for mb_history.py --csv)')
    sp.add_parser('clusters', help='<run>/sector_clusters.csv (S4)', description=doc_part('S4'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p = sp.add_parser('stage', help='<run>/sector_stage.csv (S4)', description=doc_part('S4'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--sectors', help='sectors file: also rows per sector of it')
    p.add_argument('--stage-only', action='store_true', help='recheck: only the sectors (needs --sectors)')
    p = sp.add_parser('order', help='sector of each company, gate batches reordered (S5, S6R)', description=doc_part('order'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--from-gate', action='store_true', help="the gate file's sector wins (S6R)")
    sp.add_parser('log', help='log changed sector calls (S5)', description=doc_part('log'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p = sp.add_parser('score', help='score logged sector calls (S5)', description=doc_part('log'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', help='default: <run>/sector_calls_score.md')
    a = ap.parse_args()
    return {'syms': cmd_syms, 'clusters': cmd_clusters, 'stage': cmd_stage, 'order': cmd_order,
            'log': cmd_log, 'score': cmd_score}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
