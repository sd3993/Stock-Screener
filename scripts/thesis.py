"""A company's thesis markers: S14 registers them from the agreed analysis; S11 checks them every quarter.
  python -I scripts/thesis.py register [SYM...]                    (S14)
  python -I scripts/thesis.py check <SYM>... | --all | --sectors   (S11)

---- register ----
Inputs: the company's newest analysis folder (config.analysis_dirs: runs/companies/<SYM>/<FYyyQn>/, named after the
  results quarter the analysis used) and in it the highest recheck<N>.json (the agreed analysis; only main.json:
  refused, its rechecks aren't done); data/companies/<SYM>/index.json (basis); the run's sectors.json (sector marker ids).
  Without SYMs: every company in runs/companies/ with an analysis folder.
Output: the thesis file (config.thesis_path: runs/companies/<SYM>/thesis.json): {sym, run, analysed_on, results_used,
  horizon, horizon_holds, stage (the analysis's discovery_stage), sector, basis, source (the analysis file), registered,
  markers, history: [earlier versions]}. Written only when the analysis is newer than the file's (analysed_on, then the
  analysis file); the previous content moves into history. The same analysis again: no change.
Checks (any failure: that company is not written, its problems are listed, exit 1; the analysis goes back to its
  recheck): 4-6 markers; at least 3 company-level; at least 1 sector-level whose sector_marker_id is a marker of a sector
  in sectors.json; every "script" company marker's metric in METRICS in the script; a valid op (>=, >, <=, <, between with
  [lo, hi]) and a numeric threshold wherever an op is given; a valid due date (YYYY-MM-DD) on every marker; an event
  marker names its event; basis consolidated/standalone in index.json; horizon short/medium/long; results_used FYyyQn.

---- check ----
Inputs: the thesis (config.thesis_path: sym, run, analysed_on, results_used, horizon, stage, sector, basis, markers
  [{id, level, text, metric, op, threshold, event, due, by, check, source, sector_marker_id}]); <run>/sectors.json
  (sector marker states); data/companies/<SYM>/scr/ (quarterly, profit_loss, cash_flow, balance_sheet, ratios on the
  thesis's basis: consolidated = <name>.json, standalone = <name>_standalone.json; shareholding, shp_history,
  pledge_nse, announcements, corporate_actions); facts.json `marker_inputs` {marker id: {value, unit, period, document,
  page, met}} (a filed figure read by S12; it takes precedence over the computed one).
Supported metrics (check "script"; % metrics in percent, "near" within 2 points for them):
  sales_yoy_q, pat_yoy_q   newest declared quarter vs the same quarter a year earlier (%; blank when the base <= 0)
  sales_yoy_ttm, pat_yoy_ttm   last 4 quarters vs the 4 before (%)
  opm_q, opm_ttm           OPM % of the newest quarter; operating profit / sales over the last 4 quarters (%)
  eps_ttm                  EPS of the last 4 quarters (not comparable, so no-data, when a split, bonus or consolidation
                           went ex inside those quarters or since the analysis: use pat_* then)
  sales_qoq_streak         consecutive latest quarters with sales above the quarter before (negative: falling)
  promoter_pct, promoter_chg_2q   promoters' % newest (shp_history if newer); newest minus two quarters earlier (points)
  pledge_pct               pledged % of promoter holding, newest (shp_history, else pledge_nse)
  inst_pct_chg_4q          FIIs + DIIs newest minus 4 quarters earlier (points; as sectors.py stage)
  cfo_pat_3y               cash from operations / net profit, last 3 fiscal years (ratio)
  net_debt_equity          (borrowings - cash) / (equity capital + reserves), latest balance sheet; cash from facts.json
                           (annual <year> cash_and_liquid, same basis), else gross debt (screener shows no cash line),
                           trusted only when it passes the line (a fail on gross debt is no-data)
  debtor_days              ratios, latest year
  event                    no computation: marker_inputs records it met or not; past due with nothing recorded: due-manual
  pe_pct, ret_1y           sector markers only (sector_stage.csv)
States: broken (the comparison fails; an event past due recorded as not met), near (passes within 10% of the line's
  absolute value, or 2 points for % metrics), held, pending (a "by" marker (by: true, or an event) before its due date
  that hasn't reached its line; a manual marker not yet due), due-manual (a manual marker due), no-data (the metric
  can't be computed: never passed silently). op is >=, >, <=, < or between (threshold [lo, hi]).
Integrity: announcements after analysed_on whose headline or category matches INTEGRITY in the script -> integrity review.
Half-yearly: the newest declared quarter is 2+ quarters after results_used -> re-analyse.
Action, first that applies: integrity review > re-analyse (a broken marker, the sector's marker broken in sectors.json,
  no thesis, half-yearly due) > verify (near, due-manual, no-data) > hold.
--sectors: each "script" marker of each sector in sectors.json, as the median over the sector's companies in
  sector_of.tsv (basis from index.json, else consolidated where saved), plus pe_pct and ret_1y from sector_stage.csv;
  rows with sym = <sector id>, no action row.
Output: <run>/marker_check.csv (sym, marker, level, metric, value, op, threshold, due, state, source, note, checked;
  one "action" row per company; re-running replaces that company's or sector's rows), and the same rows with the run
  appended to the company's marker-check history (config.marker_history_path). Exit 1 on bad input.
"""
import argparse, datetime as dt, glob, json, os, re, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_lib as W
import sectors as SC
from config import analysis_dirs, company_runs_dir, marker_history_path, run_dir, thesis_path, COMPANIES_DIR

INTEGRITY = re.compile(r'auditor.*resign|resignation of.*auditor|forensic|SEBI.*order|enforcement directorate|\bED\b.*(search|raid)'
                       r'|fraud|default|invocation of pledge|insolvency|NCLT', re.I)
SPLIT = re.compile(r'split|sub-?division|bonus|consolidation of shares', re.I)
PCT = {'sales_yoy_q', 'pat_yoy_q', 'sales_yoy_ttm', 'pat_yoy_ttm', 'opm_q', 'opm_ttm', 'promoter_pct', 'promoter_chg_2q',
       'pledge_pct', 'inst_pct_chg_4q', 'pe_pct', 'ret_1y'}
OPS = ('>=', '>', '<=', '<', 'between')
FIELDS = ['sym', 'marker', 'level', 'metric', 'value', 'op', 'threshold', 'due', 'state', 'source', 'note', 'checked']


class Co:
    """One company's saved data on one basis."""

    def __init__(self, sym, basis):
        self.sym, self.basis = sym, basis
        suf = '' if basis == 'consolidated' else '_standalone'
        self.q = W.scr(sym, 'quarterly' + suf)
        self.qsrc = f'scr/quarterly{suf}.json'
        if self.q and self.q.get('financial_type') not in (None, basis):
            self.q = None
        self.qr, self.qp = W.table(self.q)
        n = len(self.qr.get('Sales') or [])
        while n and (self.qr['Sales'][n - 1] is None):
            n -= 1
        self.n = n  # quarters up to the newest declared one
        self.suf = suf

    def qv(self, label, k=0):
        """Value k quarters before the newest declared one."""
        v = self.qr.get(label) or []
        i = self.n - 1 - k
        return v[i] if 0 <= i < len(v) else None

    def qsum(self, label, start, count=4):
        v = [self.qv(label, k) for k in range(start, start + count)]
        return sum(v) if None not in v and len(v) == count else None

    def newest(self):
        return self.qp[self.n - 1] if self.n else None

    def annual(self, name):
        return W.table(W.scr(self.sym, name + self.suf)), f'scr/{name}{self.suf}.json'


def pct_change(a, b):
    return (a / b - 1) * 100 if a is not None and b is not None and b > 0 else None


def corp_split_since(sym, since):
    ca = W.scr(sym, 'corporate_actions') or {}
    for r in ca.get('rows') or []:
        try:
            d = dt.datetime.strptime(r.get('exDate', ''), '%d-%b-%Y').date()
        except ValueError:
            continue
        if d >= since and SPLIT.search(r.get('subject') or ''):
            return f"{(r.get('subject') or '').strip()} ex {d}"
    return None


def shp_rows(sym):
    rows, qs = W.table(W.scr(sym, 'shareholding'))
    return rows, qs


def compute(metric, c, thesis, facts, rq):
    """(value, source, note) for one company metric."""
    sym = c.sym
    if metric in ('sales_yoy_q', 'pat_yoy_q', 'sales_yoy_ttm', 'pat_yoy_ttm', 'opm_q', 'opm_ttm', 'eps_ttm', 'sales_qoq_streak'):
        if not c.q:
            return None, c.qsrc, f'no {c.qsrc} on the {c.basis} basis'
        src = f'{c.qsrc} {c.newest()}'
        lab = 'Sales' if metric.startswith('sales') else 'Net Profit'
        if metric in ('sales_yoy_q', 'pat_yoy_q'):
            base = c.qv(lab, 4)
            if base is not None and base <= 0:
                return None, src, f'{lab} a year earlier {base}: growth not meaningful'
            return pct_change(c.qv(lab, 0), base), src, ''
        if metric in ('sales_yoy_ttm', 'pat_yoy_ttm'):
            a, b = c.qsum(lab, 0), c.qsum(lab, 4)
            if b is not None and b <= 0:
                return None, src, f'{lab} of the 4 quarters before {b}: growth not meaningful'
            return pct_change(a, b), src, ''
        if metric == 'opm_q':
            return c.qv('OPM %'), src, ''
        if metric == 'opm_ttm':
            op, s = c.qsum('Operating Profit', 0), c.qsum('Sales', 0)
            return (op / s * 100 if op is not None and s else None), src, ''
        if metric == 'eps_ttm':
            try:
                since = min(W.parse_period(c.qp[c.n - 4])[0] - dt.timedelta(days=92),
                            dt.date.fromisoformat(str(thesis.get('analysed_on'))[:10]))
            except (IndexError, ValueError, TypeError):
                since = dt.date.today() - dt.timedelta(days=455)
            sp = corp_split_since(sym, since)
            if sp:
                return None, src, f'EPS not comparable: {sp}; use pat_* markers'
            return c.qsum('EPS in Rs', 0), src, ''
        if metric == 'sales_qoq_streak':
            k, sign = 0, 0
            while True:
                a, b = c.qv('Sales', k), c.qv('Sales', k + 1)
                if a is None or b is None or a == b:
                    break
                s = 1 if a > b else -1
                if sign and s != sign:
                    break
                sign, k = s, k + 1
            return (k * sign if k else 0) if c.n >= 2 else None, src, ''
    if metric in ('promoter_pct', 'promoter_chg_2q'):
        rows, qs = shp_rows(sym)
        prom = rows.get('Promoters') or []
        hist = (W.scr(sym, 'shp_history') or {}).get('rows') or []
        h_new = hist[0] if hist else None
        newest_scr = W.parse_period(qs[-1])[0] if qs else None
        if metric == 'promoter_pct':
            try:
                hd = W.parse_period(h_new['quarter_end'])[0] if h_new else None
            except (KeyError, ValueError):
                hd = None
            if hd and h_new.get('promoter_pct') is not None and (newest_scr is None or hd > newest_scr):
                return h_new['promoter_pct'], f'scr/shp_history.json {h_new["quarter_end"]}', ''
            return (prom[-1] if prom else None), f'scr/shareholding.json {qs[-1] if qs else ""}', ''
        return ((prom[-1] - prom[-3]) if len(prom) >= 3 and None not in (prom[-1], prom[-3]) else None), 'scr/shareholding.json', ''
    if metric == 'pledge_pct':
        hist = (W.scr(sym, 'shp_history') or {}).get('rows') or []
        if hist and hist[0].get('pledged_pct_of_promoter') is not None:
            return hist[0]['pledged_pct_of_promoter'], f'scr/shp_history.json {hist[0].get("quarter_end")}', ''
        pn = (W.scr(sym, 'pledge_nse') or {}).get('rows') or []
        if pn and W.fnum(pn[0].get('percPromoterShares')) is not None:
            return W.fnum(pn[0]['percPromoterShares']), f'scr/pledge_nse.json {pn[0].get("shp")}', ''
        return None, 'scr/shp_history.json', 'no pledge figure saved'
    if metric == 'inst_pct_chg_4q':
        return SC.inst_chg(sym, rq), 'scr/shareholding.json', ''
    if metric == 'cfo_pat_3y':
        (cf, cy), cs = c.annual('cash_flow')
        (pl, py), ps = c.annual('profit_loss')
        cfo, np_ = cf.get('Cash from Operating Activity') or [], pl.get('Net Profit') or []
        yrs = [y for y in cy if y in py and not y.lower().startswith('ttm')]
        if len(yrs) < 3:
            return None, cs, 'fewer than 3 fiscal years in both cash flow and P&L'
        yrs = yrs[-3:]
        a = [cfo[cy.index(y)] if cy.index(y) < len(cfo) else None for y in yrs]
        b = [np_[py.index(y)] if py.index(y) < len(np_) else None for y in yrs]
        if None in a or None in b or sum(b) <= 0:
            return None, f'{cs}, {ps}', f'years {yrs}: missing values or net profit <= 0'
        return sum(a) / sum(b), f'{cs}, {ps} {yrs[0]}-{yrs[-1]}', ''
    if metric == 'net_debt_equity':
        (bs, by), s = c.annual('balance_sheet')
        if not by:
            return None, s, 'no balance sheet'
        g = lambda k: (bs.get(k) or [None])[-1]
        eq = (g('Equity Capital') or 0) + (g('Reserves') or 0) if g('Reserves') is not None else None
        debt = g('Borrowings')
        # facts.json (S12): annual {period: {cash_and_liquid: {value, basis, ...}}} for the balance sheet's year and basis
        f = (((facts or {}).get('annual') or {}).get(by[-1]) or {}).get('cash_and_liquid') or {}
        cash = W.fnum(f.get('value')) if f.get('basis') in (None, c.basis) else None
        if debt is None or not eq or eq <= 0:
            return None, s, 'borrowings or equity missing (or equity <= 0)'
        if cash is None:
            return debt / eq, f'{s} {by[-1]}', 'GROSS debt / equity (no cash figure saved)'
        return (debt - cash) / eq, f'{s} {by[-1]} + facts.json cash', ''
    if metric == 'debtor_days':
        (ra, ry), s = c.annual('ratios')
        v = ra.get('Debtor Days') or []
        return (v[-1] if v else None), f'{s} {ry[-1] if ry else ""}', ''
    return None, '', f'metric {metric!r} not supported'


METRICS = ['sales_yoy_q', 'pat_yoy_q', 'sales_yoy_ttm', 'pat_yoy_ttm', 'opm_q', 'opm_ttm', 'eps_ttm', 'sales_qoq_streak',
           'promoter_pct', 'promoter_chg_2q', 'pledge_pct', 'inst_pct_chg_4q', 'cfo_pat_3y', 'net_debt_equity', 'debtor_days', 'event']
SECTOR_ONLY = ['pe_pct', 'ret_1y']


def compare(v, op, thr, metric):
    """(passes, near)."""
    if op == 'between':
        lo, hi = thr
        ok = lo <= v <= hi
        lines = (lo, hi)
    else:
        ok = {'>=': v >= thr, '>': v > thr, '<=': v <= thr, '<': v < thr}[op]
        lines = (thr,)
    margin = lambda L: 2.0 if metric in PCT else abs(L) * 0.10
    near = ok and any(abs(v - L) <= margin(L) for L in lines)
    return ok, near


def parse_due(m):
    try:
        return dt.date.fromisoformat(str(m.get('due'))[:10]) if m.get('due') else None
    except ValueError:
        return None


def state_of(m, value, note, today, inputs):
    """Marker state from a value (or marker_inputs for events/manual)."""
    due, op, thr = parse_due(m), m.get('op'), m.get('threshold')
    by = bool(m.get('by')) or m.get('metric') == 'event'
    inp = (inputs or {}).get(str(m.get('id')))
    if m.get('metric') == 'event' or (m.get('check') == 'manual' and not (inp and W.fnum(inp.get('value')) is not None)):
        if inp and 'met' in inp:
            return ('held' if inp['met'] else ('broken' if not due or due <= today else 'pending')), 'facts.json marker_inputs'
        if m.get('check') == 'manual' or m.get('metric') == 'event':
            return ('due-manual' if due and due <= today else 'pending'), note or 'manual / event'
    if value is None:
        return 'no-data', note
    if op not in OPS or thr is None or (op == 'between' and not (isinstance(thr, list) and len(thr) == 2)):
        return 'no-data', f'bad op/threshold {op} {thr}'
    ok, near = compare(value, op, thr, m.get('metric'))
    if 'GROSS debt' in (note or '') and not ok:
        return 'no-data', note + ': fails gross, cash unknown'
    if not ok:
        return ('pending' if by and due and due > today else 'broken'), note
    return ('near' if near else 'held'), note


def load_facts(sym):
    p = os.path.join(W.COMPANIES_DIR, sym, 'facts.json')
    try:
        return W.read_json(p)
    except (OSError, ValueError):
        return {}


def basis_of(sym, thesis):
    b = (thesis or {}).get('basis')
    if b:
        return b
    try:
        return W.read_json(os.path.join(W.COMPANIES_DIR, sym, 'index.json')).get('basis')
    except (OSError, ValueError):
        return None


def check_company(sym, run, today, sectors):
    rq = SC.run_quarter(run)
    tp = thesis_path(sym)
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    row = lambda **k: {**{f: '' for f in FIELDS}, 'sym': sym, 'checked': now, **k}
    if not os.path.exists(tp):
        return [row(marker='action', state='re-analyse', note='no thesis')]
    try:
        th = W.read_json(tp)
    except ValueError as e:
        return [row(marker='action', state='re-analyse', note=f'thesis not readable: {e}')]
    out, reasons = [], {'integrity review': [], 're-analyse': [], 'verify': []}
    basis = th.get('basis')
    if basis not in ('consolidated', 'standalone'):
        reasons['verify'].append('thesis has no basis (consolidated/standalone): statement metrics not checked')
    c = Co(sym, basis or 'consolidated')
    facts = load_facts(sym)
    inputs = facts.get('marker_inputs') or {}
    sec = next((s for s in sectors if s.get('id') == th.get('sector')), None)
    smk = {str(m.get('id')): m for m in (sec or {}).get('markers') or []}
    for m in th.get('markers') or []:
        metric, mid = m.get('metric'), str(m.get('id'))
        if m.get('level') == 'sector':
            sm = smk.get(str(m.get('sector_marker_id')))
            if not sm:
                stt, note, v = 'no-data', f'sector marker {m.get("sector_marker_id")} not in sectors.json', None
            else:
                v = sm.get('state')
                stt = {'held': 'held', 'near': 'near', 'broken': 'broken'}.get(sm.get('state'))
                due = parse_due(m)
                stt = stt or ('due-manual' if due and due <= today else 'pending')
                note = f'sectors.json state {sm.get("state")} {sm.get("state_date") or ""}'.strip()
            out.append(row(marker=mid, level='sector', metric=metric, value=v, op=m.get('op'), threshold=json.dumps(m.get('threshold')),
                           due=m.get('due'), state=stt, source='sectors.json', note=note))
            continue
        inp = inputs.get(mid)
        if inp and W.fnum(inp.get('value')) is not None:
            v, src, note = W.fnum(inp['value']), f"facts.json marker_inputs ({inp.get('document', '')} p{inp.get('page', '')})", ''
        elif metric == 'event' or m.get('check') == 'manual':
            v, src, note = None, '', ''
        elif basis not in ('consolidated', 'standalone') and metric not in ('promoter_pct', 'promoter_chg_2q', 'pledge_pct', 'inst_pct_chg_4q'):
            v, src, note = None, '', 'no basis in the thesis'
        else:
            v, src, note = compute(metric, c, th, facts, rq)
        stt, note = state_of(m, v, note, today, inputs)
        out.append(row(marker=mid, level=m.get('level', 'company'), metric=metric, value='' if v is None else round(v, 3),
                       op=m.get('op'), threshold=json.dumps(m.get('threshold')), due=m.get('due'), state=stt, source=src, note=note or ''))
    for r in out:
        if r['state'] == 'broken':
            reasons['re-analyse'].append(f"marker {r['marker']} broken")
        elif r['state'] in ('near', 'due-manual', 'no-data'):
            reasons['verify'].append(f"marker {r['marker']} {r['state']}")
    if sec and any(sm.get('state') == 'broken' for sm in smk.values()):
        reasons['re-analyse'].append(f"sector {sec['id']} marker broken")
    if th.get('sector') and not sec:
        reasons['verify'].append(f"sector {th.get('sector')} not in sectors.json")
    # half-yearly
    nq = c.newest() if c.q else None
    if not nq:  # the other basis may still show the newest declared quarter
        c2 = Co(sym, 'standalone' if c.basis == 'consolidated' else 'consolidated')
        nq = c2.newest()
    try:
        if nq and th.get('results_used') and W.fyq_index(W.fyq_of_label(nq)) - W.fyq_index(th['results_used']) >= 2:
            reasons['re-analyse'].append(f"half-yearly re-analysis due: newest declared {W.fyq_of_label(nq)}, thesis used {th['results_used']}")
    except ValueError:
        reasons['verify'].append(f"results_used {th.get('results_used')!r} not a quarter name")
    # integrity
    try:
        since = dt.date.fromisoformat(str(th.get('analysed_on'))[:10])
    except ValueError:
        since = dt.date.today() - dt.timedelta(days=365)
        reasons['verify'].append('analysed_on missing: integrity scan over the last 12 months')
    ann = W.scr(sym, 'announcements')
    if ann is None:
        reasons['verify'].append('no announcements.json: integrity scan not done')
    for x in (ann or {}).get('announcements') or []:
        try:
            d = dt.datetime.strptime(x.get('date', '')[:11], '%d-%b-%Y').date()
        except ValueError:
            continue
        text = ' '.join(str(x.get(k) or '') for k in ('headline', 'category', 'nse_category'))
        if d > since and INTEGRITY.search(text):
            reasons['integrity review'].append(f"{d}: {x.get('headline', '')[:150]}")
    act = next((k for k in ('integrity review', 're-analyse', 'verify') if reasons[k]), 'hold')
    out.append(row(marker='action', state=act, note=' | '.join(reasons[act]) if act != 'hold' else 'every marker held or pending'))
    return out


def check_sectors(run, today, sectors):
    rq = SC.run_quarter(run)
    sp = os.path.join(run, 'sector_of.tsv')
    mem = {}
    if os.path.exists(sp):
        for r in W.read_csv(sp, delimiter='\t'):
            mem.setdefault(r['sector'], []).append(r['sym'])
    stg = {}
    gp = os.path.join(run, 'sector_stage.csv')
    if os.path.exists(gp):
        stg = {r['id']: r for r in W.read_csv(gp) if r['kind'] == 'sector'}
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    out = []
    for s in sectors:
        for m in s.get('markers') or []:
            if m.get('check') != 'script':
                continue
            metric = m.get('metric')
            if metric in SECTOR_ONLY:
                v = W.fnum((stg.get(s['id']) or {}).get(metric))
                src, note, n = 'sector_stage.csv', '' if v is not None else 'no sector_stage.csv row', ''
            else:
                vals = []
                for sym in mem.get(s['id'], []):
                    b = basis_of(sym, None) or ('consolidated' if os.path.exists(W.scr_path(sym, 'quarterly')) else 'standalone')
                    v1, _, _ = compute(metric, Co(sym, b), {}, load_facts(sym), rq)
                    if v1 is not None:
                        vals.append(v1)
                v = st.median(vals) if vals else None
                src, note = f'median of {len(vals)} of {len(mem.get(s["id"], []))} companies (sector_of.tsv)', '' if vals else 'no member value'
            stt, note = state_of(m, v, note, today, {})
            out.append({'sym': s['id'], 'marker': str(m.get('id')), 'level': 'sector', 'metric': metric,
                        'value': '' if v is None else round(v, 3), 'op': m.get('op'), 'threshold': json.dumps(m.get('threshold')),
                        'due': m.get('due'), 'state': stt, 'source': src, 'note': note or '', 'checked': now})
    return out


# ---------- register ----------
KEEP = ('sym', 'run', 'analysed_on', 'results_used', 'horizon', 'horizon_holds', 'stage', 'sector', 'basis', 'source', 'registered', 'markers')


def agreed(sym):
    """The agreed analysis: the highest recheck<N>.json in the company's newest analysis folder."""
    dirs = analysis_dirs(sym)
    if not dirs:
        return None, 'no analysis folder'
    files = []
    for fn in glob.glob(os.path.join(dirs[-1], 'recheck*.json')):
        m = re.match(r'recheck(\d+)\.json$', os.path.basename(fn))
        if m:
            files.append((int(m.group(1)), fn))
    return (max(files)[1], '') if files else (None, f'no recheck<N>.json in {dirs[-1]} (only main.json, or nothing): not agreed yet')


def validate(a, basis, marker_ids):
    p = []
    ms = a.get('markers') or []
    if not 4 <= len(ms) <= 6:
        p.append(f'{len(ms)} markers (4-6 needed)')
    comp = [m for m in ms if m.get('level') == 'company']
    sect = [m for m in ms if m.get('level') == 'sector']
    if len(comp) < 3:
        p.append(f'{len(comp)} company-level markers (3+ needed)')
    if not sect:
        p.append('no sector-level marker')
    for m in sect:
        if str(m.get('sector_marker_id')) not in marker_ids:
            p.append(f'marker {m.get("id")}: sector_marker_id {m.get("sector_marker_id")!r} not a marker in sectors.json')
    for m in ms:
        i = m.get('id')
        if m.get('level') not in ('company', 'sector'):
            p.append(f'marker {i}: level {m.get("level")!r} (company/sector)')
        if m.get('check') not in ('script', 'manual'):
            p.append(f'marker {i}: check {m.get("check")!r} (script/manual)')
        if m.get('check') == 'script' and m.get('level') == 'company' and m.get('metric') not in METRICS:
            p.append(f'marker {i}: metric {m.get("metric")!r} not supported by thesis.py check')
        if m.get('metric') == 'event' and not m.get('event'):
            p.append(f'marker {i}: event marker without its event')
        op, thr = m.get('op'), m.get('threshold')
        if op or (m.get('check') == 'script' and m.get('level') == 'company' and m.get('metric') != 'event'):
            if op not in OPS:
                p.append(f'marker {i}: op {op!r}')
            elif op == 'between':
                if not (isinstance(thr, list) and len(thr) == 2 and all(isinstance(x, (int, float)) for x in thr) and thr[0] <= thr[1]):
                    p.append(f'marker {i}: between needs [lo, hi], got {thr!r}')
            elif not isinstance(thr, (int, float)) or isinstance(thr, bool):
                p.append(f'marker {i}: threshold {thr!r} not a number')
        try:
            dt.date.fromisoformat(str(m.get('due')))
        except ValueError:
            p.append(f'marker {i}: due {m.get("due")!r} not YYYY-MM-DD')
    if basis not in ('consolidated', 'standalone'):
        p.append(f'basis {basis!r} in index.json (consolidated/standalone needed)')
    if a.get('horizon') not in ('short', 'medium', 'long'):
        p.append(f'horizon {a.get("horizon")!r}')
    for k in ('analysed_on', 'results_used'):
        if not a.get(k):
            p.append(f'{k} missing')
    if a.get('results_used') and not W.QRE.match(str(a['results_used'])):
        p.append(f'results_used {a["results_used"]!r} not FYyyQn')
    return p




def cmd_register(a):
    run = run_dir()
    mp = os.path.join(run, 'sectors.json')
    marker_ids = set()
    if os.path.exists(mp):
        for s in W.read_json(mp).get('sectors') or []:
            marker_ids |= {str(m.get('id')) for m in s.get('markers') or []}
    else:
        print(f'note: no {mp}: sector markers cannot be matched')
    root = company_runs_dir()
    syms = a.syms or sorted(x for x in (os.listdir(root) if os.path.isdir(root) else ()) if analysis_dirs(x))
    if not syms:
        W.fail(f'no analyses in {root}')
    written, same, problems = [], [], {}
    for sym in syms:
        fn, why = agreed(sym)
        if not fn:
            problems[sym] = [why]
            continue
        try:
            an = W.read_json(fn)
        except ValueError as e:
            problems[sym] = [f'{fn} not JSON: {e}']
            continue
        try:
            basis = W.read_json(os.path.join(COMPANIES_DIR, sym, 'index.json')).get('basis')
        except (OSError, ValueError):
            basis = None
        p = validate(an, basis, marker_ids)
        if p:
            problems[sym] = p
            continue
        tp = thesis_path(sym)
        old = W.read_json(tp) if os.path.exists(tp) else None
        src = fn.replace('\\', '/')
        if old and (str(old.get('analysed_on')), old.get('source')) == (str(an.get('analysed_on')), src):
            same.append(sym)
            continue
        if old and str(old.get('analysed_on')) > str(an.get('analysed_on')):
            same.append(f'{sym} (thesis newer than {src})')
            continue
        new = {'sym': sym, 'run': os.path.basename(os.path.normpath(run)), 'analysed_on': an.get('analysed_on'),
               'results_used': an.get('results_used'), 'horizon': an.get('horizon'), 'horizon_holds': an.get('horizon_holds', True),
               'stage': an.get('discovery_stage'), 'sector': an.get('sector'), 'basis': basis, 'source': src,
               'registered': dt.date.today().isoformat(), 'markers': an.get('markers'),
               'history': ((old or {}).get('history') or []) + ([{k: old.get(k) for k in KEEP}] if old else [])}
        W.write_json(tp, new)
        written.append(sym)
    print(f'{len(written)} theses written {written or ""}; {len(same)} unchanged {same or ""}; {len(problems)} refused')
    for s, p in problems.items():
        print(f'REFUSED {s}: ' + '; '.join(p))
    return 1 if problems else 0


# ---------- check (main) ----------
def cmd_check(a):
    run, today = run_dir(), dt.date.today()
    if not (a.syms or a.all or a.sectors):
        W.fail('give symbols, --all or --sectors')
    mp = os.path.join(run, 'sectors.json')
    sectors = []
    if os.path.exists(mp):
        try:
            sectors = W.read_json(mp).get('sectors') or []
        except ValueError as e:
            W.fail(f'{mp}: not JSON ({e})')
    elif a.sectors:
        W.fail(f'{mp} missing')
    syms = list(a.syms)
    if a.all:
        syms += sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(thesis_path('*')))
    new = []
    for s in dict.fromkeys(syms):
        new += check_company(s, run, today, sectors)
    if a.sectors:
        new += check_sectors(run, today, sectors)
    out = os.path.join(run, 'marker_check.csv')
    done = {r['sym'] for r in new}
    old = [r for r in W.read_csv(out) if r['sym'] not in done] if os.path.exists(out) else []
    W.write_csv(out, FIELDS, old + new)
    rn = os.path.basename(os.path.normpath(run))
    for s in dict.fromkeys(syms):  # each company's marker-check history: this check appended
        W.append_csv(marker_history_path(s), ['run'] + FIELDS, [dict(r, run=rn) for r in new if r['sym'] == s])
    acts = [(r['sym'], r['state'], r['note']) for r in new if r['marker'] == 'action']
    for s, act, note in acts:
        print(f'{s}: {act.upper()}' + (f' ({note})' if note else ''))
    sec_rows = [r for r in new if r['level'] == 'sector' and r['sym'] not in syms]
    if a.sectors:
        print(f'sector markers checked: {len(sec_rows)} ' + str({k: sum(r["state"] == k for r in sec_rows) for k in ("held", "near", "broken", "pending", "due-manual", "no-data")}))
    print(f'{len(acts)} companies, {sum(r["marker"] != "action" for r in new)} marker rows -> {out}')
    return 0


def doc_part(head):
    """A mode's --help: the docstring's usage lines plus its '---- <head>' section."""
    parts = __doc__.split('\n---- ')
    return parts[0] + '\n---- ' + next(p for p in parts[1:] if p.startswith(head))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True, help='the mode; <mode> --help for its own help')
    p = sp.add_parser('register', help='register thesis markers from the agreed analysis (S14)', description=doc_part('register'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('syms', nargs='*', help='symbols (default: every company in runs/companies/ with an analysis folder)')
    p = sp.add_parser('check', help='check thesis markers (S11)', description=doc_part('check'), formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('syms', nargs='*', help='symbols to check (give symbols, --all or --sectors)')
    p.add_argument('--all', action='store_true', help='every company with a thesis file')
    p.add_argument('--sectors', action='store_true', help="each sector's script markers (see above)")
    a = ap.parse_args()
    return cmd_register(a) if a.cmd == 'register' else cmd_check(a)


if __name__ == '__main__':
    sys.exit(main())
