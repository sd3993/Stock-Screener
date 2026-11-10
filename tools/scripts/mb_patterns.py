import argparse, ast, bisect, collections, csv, datetime as dt, hashlib, json, math, os, random, re, statistics, sys, time
# Study and playbook features, S6 (process/s6_playbook.md, steps 2-8; tests in process/s6_playbook.md, "Pattern tests").
# Staged tests, one subcommand per round. No fetching; nothing here writes outcomes.csv, sample.csv or a features file.
#   python -I tools/scripts/mb_patterns.py scan [--features FILE[,FILE]]     # steps 2-3: winners, then market lift (chart features)
#   python -I tools/scripts/mb_patterns.py panel [--seed 1] [--n 3]          # step 4: peer_panel.csv, peer_untagged.csv
#   python -I tools/scripts/mb_patterns.py peers [--panel-features FILE]     # steps 4-5: panel / same-type lift, matched pairs
#   python -I tools/scripts/mb_patterns.py market_fetch [--force]            # market_fetch.txt (statements for the market test)
#   python -I tools/scripts/mb_patterns.py test  [--tag-limit 200]           # steps 6-7: 2016-2023 unchanged; whole market
#   python -I tools/scripts/mb_patterns.py exits [--write-rows] [--exit-features FILE]   # step 8
#   common: --dir DIR (reads and writes there, default the newest study run), --out FILE (patterns.csv), --features,
#           --market-features FILE (default <dir>/market_features.csv), --companies DIR, --force (redo a finished stage)
# After `panel`: mb_features.py --rows peer_panel.csv --out features_panel.csv; bse_shp.py --rows peer_panel.csv;
#   ar_statements.py plan --rows peer_panel.csv --groups peer (its default --groups drops group=peer rows).
#
# patterns.csv: one row per pattern, horizon and scope (overall or a business type), each stage's figures with counts;
# stage_failed names the first stage it failed (blank = still alive). Stages run independently per row, so a pattern that
# fails overall can stay alive within a type (README test 6). Finished stages are skipped on a re-run (done_* columns).
# patterns_meta.json: the number of patterns tried, types with too few winners, and a hash of the fixed list: a changed list
# or threshold is refused unless --force, because the list must be set before the scan.
#
# How each figure is built:
#   Winners, chart features: every company in outcomes.csv meeting the horizon's threshold (mb_sample.py's test) at a start in
#     the set with mc0 >= 50, on windows passing mb_sample.artefacts (market_winners_disc.csv, _test.csv: every window's
#     result, resumable; --refresh rebuilds). Each company counts once per horizon and feature: its first qualifying window where
#     the feature can be judged, chosen without looking at its value; w_known of w_total companies. A business-type scope takes
#     the tagged winners. Winners, statements and shareholding: sample.csv group=winner and the panel.
#     Discovery = starts 2006-2015, test = 2016-2023 (and within the horizon's last start). scan and panel load only discovery
#     rows from every file (Data y1=2015), so no later row can affect them (a window's outcome and its artefact check read
#     prices to its end, past 2015 for late discovery starts).
#   Same-date thirds: cut-offs from every company >= Rs 50 cr on that date in market_features.csv (never across dates). A
#     statement or shareholding feature has no such distribution until market statements exist, so its thirds are
#     "deferred" at scan and measured in `peers`, from the panel's rows on that date (at least PANEL_DIST).
#   Market lift: freq among winners / share among companies below the winner threshold in the winner's (start date, size
#     band), each cell weighted by its winners with the feature known; cells with under MIN_CELL comparison companies drop
#     out of both sides. Missing stays unknown: never counted as passing or failing.
#   Peer lift: per winner, the share among its own panel peers (fundamentals) or among all same-type tagged companies on its
#     date below the threshold (chart features), averaged over winners; by band, peers in the winner's band only.
#   Restatement: a statement pattern that reaches 50% only with rows flagged stmt_gap_fy fails as 'restated'.
#   Exits: signals at each quarter-end from the first quarter-end at or above the threshold to the window's end, for both
#     groups, so no signal uses the peak; the group label uses the window's outcome. Fall = a later quarter-end price at
#     or below half the signal date's price within FALL_YEARS.
# Not testable as written: NOT_TESTED, listed in patterns.csv as kind=not_tested with the reason.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir

FREQ_MIN, LIFT_MIN = 0.5, 1.5
MIN_TYPE_WINNERS = 15  # a business type with fewer winners in a horizon is reported as too few
MIN_KNOWN = 10         # fewest winners with the feature known for a frequency to count
MIN_CELL = 5           # fewest comparison companies in a (date, band) cell; fewest winners for a regime or band to count
MIN_DIST, PANEL_DIST = 30, 6  # fewest values for a same-date third, from the market / from the panel
N_PEERS, SEED, TAG_LIMIT = 3, 1, 200
FALL, FALL_YEARS = 0.5, 2
NEARBY = (0.8, 1.2)    # thresholds moved by this factor; thirds moved by PCT_NEARBY
PCT_NEARBY = 0.067
DISC, TEST = (2006, 2015), (2016, 2023)
REGIMES = (('2006-10', 2006, 2010), ('2011-15', 2011, 2015), ('2016-19', 2016, 2019), ('2020-23', 2020, 2023))
# As in mb_sample.py, which can't be imported (it runs on import and rewrites sample_candidates.csv).
WIN = {'short': (['px_2y'], 2, '2023-12-31', 2), 'medium': (['px_5y'], 3, '2021-12-31', 5), 'long': (['px_7y', 'px_10y'], 10, '2019-12-31', 7)}
MIN_MC = 50
CLOSE_STEP = '0.5-2x'  # mb_sample.py STEPS[0]


def band(mc):
    return '50-500' if mc < 500 else '500-2k' if mc < 2000 else '2k-10k' if mc < 10000 else '10k+'


# --- the fixed list: set before the scan -------------------------------------------------------------------------------
CHART_NUM = ['mcap_cr', 'eps_g1', 'eps_g3', 'eps_g5', 'eps_acc', 'sales_g1', 'sales_g3', 'sales_g5', 'sales_acc', 'pe', 'pe_rel5',
             'peg3', 'peg1', 'ps', 'px_ret1', 'px_ret6m', 'px_ret3', 'px_off_hi52', 'shares_chg1', 'shares_chg3', 'tv13_med_cr']
CHART_BIN = ['loss_ttm', 'eps_g1_rising2q', 'sales_g1_rising2q']
CHART_DERIVED = ['pe_rel_mkt', 'mc_rank']  # same-date, from the market table
STMT_NUM = ['fy_sales_g1', 'fy_sales_g3', 'fy_np_g1', 'fy_np_g3', 'fy_eps_g1', 'fy_eps_g3', 'opm', 'opm_chg3', 'opm_vs_avg3', 'payout',
            'oi_share_pbt', 'tax_pct', 'int_cover', 'de', 'eq_cap_chg3', 'roe', 'roe_avg3', 'debt_ebitda', 'roce', 'roce_avg3',
            'roce_min3', 'debtor_days', 'wc_days', 'ccc_days', 'cfo_pat_2y', 'cfo_pat_3y', 'cfo_pat_5y', 'fscore8',
            'q_sales_yoy', 'q_eps_yoy', 'q_np_yoy', 'q_opm', 'q_opm_yoy_chg']
STMT_BIN = ['q_sales_yoy_rising2q', 'q_eps_yoy_rising2q', 'q_np_yoy_rising2q', 'q_accel', 'q_sales_opm_fall2q']
SHP_NUM = ['prom_pct', 'prom_chg_1y', 'prom_chg_3y', 'pledge_pct', 'inst_pct', 'inst_chg_1y']
SHP_BIN = ['pledge_new_4q']
ATTRS = {'cyclicality': ('low', 'medium', 'high'), 'capital_intensity': ('low', 'medium', 'high'),
         'pricing_power': ('low', 'medium', 'high')}
CUSTOMERS = ('B2C', 'B2B', 'government')
CHART = set(CHART_NUM + CHART_BIN + CHART_DERIVED)
STMT = set(STMT_NUM + STMT_BIN)
TEXT = set(ATTRS) | {'customers', 'stmt_gap_fy'}
ALL_FEATS = CHART_NUM + CHART_BIN + CHART_DERIVED + STMT_NUM + STMT_BIN + SHP_NUM + SHP_BIN + list(TEXT)
META = ['mc0', 'px0', 'px_2y', 'px_5y', 'px_7y', 'px_10y', 'mc_2y', 'mc_5y', 'mc_7y', 'mc_10y', 'pxpeak_2y', 'pxpeak_5y', 'pxpeak_7y', 'pxpeak_10y']
COLS = META + ALL_FEATS
IX = {c: i for i, c in enumerate(COLS)}
OUTCOME_FALLBACK = {'pe': 'pe0', 'eps_g1': 'eps_g1', 'eps_g3': 'eps_g3', 'sales_g1': 'sales_g1', 'sales_g3': 'sales_g3', 'px_ret1': 'px_ret1'}

# Explicit thresholds: (id, source, legs, options). Leg: (feature, op, a[, b]); 'btw' is a <= v < b. Options: h = horizons,
# min_mc = universe floor, rule = a current rule's pass test (step 7 counts its misses and false alarms), note.
HYP = 'experts.md '
RULE = 'investing_rules.md '
THRESHOLDS = [
    ('H1.pe_lt10', HYP + 'H1', [('pe', '<', 10)], {'min_mc': 1000}),
    ('H1.pe_10_20', HYP + 'H1', [('pe', 'btw', 10, 20)], {'min_mc': 1000}),
    ('H1.pe_20_30', HYP + 'H1', [('pe', 'btw', 20, 30)], {'min_mc': 1000}),
    ('H1.pe_30_50', HYP + 'H1', [('pe', 'btw', 30, 50)], {'min_mc': 1000}),
    ('H1.pe_50_75', HYP + 'H1', [('pe', 'btw', 50, 75)], {'min_mc': 1000}),
    ('H1.pe_ge75', HYP + 'H1', [('pe', '>=', 75)], {'min_mc': 1000}),
    ('H2.rel_le1', HYP + 'H2', [('pe_rel_mkt', '<=', 1)], {}),
    ('H2.rel_1_2', HYP + 'H2', [('pe_rel_mkt', 'btw', 1, 2)], {}),
    ('H2.rel_2_3', HYP + 'H2', [('pe_rel_mkt', 'btw', 2, 3)], {}),
    ('H2.rel_gt3', HYP + 'H2', [('pe_rel_mkt', '>=', 3)], {}),
    ('H3.below_own5', HYP + 'H3', [('pe_rel5', '<', 1)], {'note': 'partial: 5-year median only; Consistent/Volatile split not built'}),
    ('H3.above_own5', HYP + 'H3', [('pe_rel5', '>=', 1)], {'note': 'partial: 5-year median only'}),
    ('H4.peg_0_05', HYP + 'H4', [('peg3', 'btw', 0, 0.5)], {}),
    ('H4.peg_05_1', HYP + 'H4', [('peg3', 'btw', 0.5, 1)], {}),
    ('H4.peg_1_2', HYP + 'H4', [('peg3', 'btw', 1, 2)], {}),
    ('H4.peg_2_3', HYP + 'H4', [('peg3', 'btw', 2, 3)], {}),
    ('H4.peg_ge3', HYP + 'H4', [('peg3', '>=', 3)], {}),
    ('H4.eps_g3_neg', HYP + 'H4', [('eps_g3', '<=', 0)], {'note': 'negative PEG: trailing growth at or below zero'}),
    ('H5.eps_g5_25', HYP + 'H5', [('eps_g5', '>=', 25)], {}),
    ('H5.eps_g3_25', HYP + 'H5', [('eps_g3', '>=', 25)], {}),
    ('H6.roe15_pe20', HYP + 'H6', [('roe', '>=', 15), ('pe', '<=', 20)], {'note': 'partial: first crossing in 10+ years not computable from features; PAT floor not built'}),
    ('H7.mid_to_mega', HYP + 'H7', [('mc_rank', 'btw', 101, 301), ('roe', '>=', 20), ('fy_np_g3', '>=', 20), ('pe', '<=', 25), ('cyclicality', '!=', 'high')],
     {'note': 'partial: 3-year PAT CAGR for 2-year'}),
    ('H8.mc_lt500', HYP + 'H8', [('mcap_cr', '<', 500)], {}),
    ('H8.mc_500_3k', HYP + 'H8', [('mcap_cr', 'btw', 500, 3000)], {}),
    ('H8.mc_3k_10k', HYP + 'H8', [('mcap_cr', 'btw', 3000, 10000)], {}),
    ('H8.mc_10k_25k', HYP + 'H8', [('mcap_cr', 'btw', 10000, 25000)], {}),
    ('H8.mc_ge25k', HYP + 'H8', [('mcap_cr', '>=', 25000)], {}),
    ('H10.pe_le20', HYP + 'H10', [('pe', '<=', 20)], {'h': ['long']}),
    ('H10.pe_ge50', HYP + 'H10', [('pe', '>=', 50)], {'h': ['long']}),
    ('H12.mom_top5th', HYP + 'H12', [('px_ret1', 'pct>=', 0.8)], {'note': 'partial: 12-month return, not 12-1'}),
    ('H16.roe15_np15', HYP + 'H16', [('roe_avg3', '>', 15), ('fy_np_g3', '>', 15)], {'note': 'partial: 3 years for the 10 in the hypothesis'}),
    ('H18.bruised', HYP + 'H18', [('roe_avg3', '>=', 20), ('px_off_hi52', '<=', -0.5)], {'note': 'partial: 3-year ROE, 52-week high, no P/B'}),
    ('H19.de_gt08', HYP + 'H19', [('de', '>', 0.8)], {}),
    ('H19.cover_lt3', HYP + 'H19', [('int_cover', '<', 3)], {}),
    ('H19.debt_ebitda_gt25', HYP + 'H19', [('debt_ebitda', '>', 2.5)], {}),
    ('H20.cfo_ge065', HYP + 'H20', [('cfo_pat_5y', '>=', 0.65)], {}),
    ('H20.cfo_04_065', HYP + 'H20', [('cfo_pat_5y', 'btw', 0.4, 0.65)], {}),
    ('H20.cfo_lt04', HYP + 'H20', [('cfo_pat_5y', '<', 0.4)], {}),
    ('R1.1.pledge_zero', RULE + '1.1', [('pledge_pct', '==', 0)], {'rule': 1}),
    ('R1.1.pledge_le20', RULE + '1.1', [('pledge_pct', '<=', 20)], {'rule': 1}),
    ('R1.1.no_new_pledge', RULE + '1.1', [('pledge_new_4q', '==', 0)], {'rule': 1}),
    ('R1.4.cfo3_065', RULE + '1.4', [('cfo_pat_3y', '>=', 0.65)], {'rule': 1}),
    ('R1.4.cfo5_065', RULE + '1.4', [('cfo_pat_5y', '>=', 0.65)], {'rule': 1}),
    ('R3.prom_50', RULE + '3', [('prom_pct', '>=', 50)], {'rule': 1}),
    ('R3.prom_40', RULE + '3', [('prom_pct', '>=', 40)], {'rule': 1}),
    ('R3.prom_fall_le5', RULE + '3', [('prom_chg_3y', '>=', -5)], {'rule': 1}),
    ('R4.de_lt08', RULE + '4', [('de', '<', 0.8)], {'rule': 1, 'note': 'gross debt: features have no net debt'}),
    ('R4.cover_3', RULE + '4', [('int_cover', '>=', 3)], {'rule': 1}),
    ('R4.debt_ebitda', RULE + '4', [('debt_ebitda', '<=', 2.5)], {'rule': 1, 'note': 'gross debt'}),
    ('R5.debtors_120', RULE + '5', [('debtor_days', '<=', 120)], {'rule': 1}),
    ('R6.acceleration', RULE + '6 short (a)', [('q_accel', '==', 1)], {'rule': 1, 'h': ['short']}),
    ('R6.stalwart', RULE + '6 short (b)', [('roce', '>', 20), ('pe_rel5', '<', 1), ('eps_g1', '>', 0)], {'rule': 1, 'h': ['short']}),
    ('R6.long_quality', RULE + '6 long', [('eps_g3', '>=', 25), ('roce', '>', 20)], {'rule': 1, 'h': ['long']}),
    ('R8.pe_lt50', RULE + '8', [('pe', '<', 50)], {'rule': 1, 'note': 'trailing P/E: the rule is on forward earnings, not known at the time'}),
    ('R9.mc_lt25k', RULE + '9 medium', [('mcap_cr', '<', 25000)], {'rule': 1, 'h': ['medium']}),
    ('R9.mc_lt5k', RULE + '9 long', [('mcap_cr', '<', 5000)], {'rule': 1, 'h': ['long']}),
]
# Step 8: H14, H15, rule 12 and the plain deteriorations. Each is what could be seen at the quarter-end.
EXIT_SIGNALS = [
    ('X.pe_gt50', RULE + '12; ' + HYP + 'H15', [('pe', '>', 50)]),
    ('X.pe_gt2x_mkt', HYP + 'H15', [('pe_rel_mkt', '>', 2)]),
    ('X.peg_gt3', HYP + 'H15', [('peg3', '>', 3)]),
    ('X.top100', HYP + 'H15', [('mc_rank', '<=', 100)]),
    ('X.mc_gt15k', RULE + '12', [('mcap_cr', '>', 15000)]),
    ('X.mc_gt20k', RULE + '12', [('mcap_cr', '>', 20000)]),
    ('X.sales_opm_fall2q', RULE + '12; ' + HYP + 'H14', [('q_sales_opm_fall2q', '==', 1)]),
    ('X.off_hi52_30', 'fixed list', [('px_off_hi52', '<=', -0.3)]),
    ('X.off_hi52_50', 'fixed list', [('px_off_hi52', '<=', -0.5)]),
    ('X.eps_g1_neg', 'fixed list', [('eps_g1', '<', 0)]),
    ('X.sales_g1_neg', 'fixed list', [('sales_g1', '<', 0)]),
    ('X.eps_acc_neg', 'fixed list', [('eps_acc', '<', 0)]),
    ('X.pe_rel5_gt15', 'fixed list', [('pe_rel5', '>', 1.5)]),
    ('X.pe_rel5_gt2', 'fixed list', [('pe_rel5', '>', 2)]),
    ('X.dilution_5', 'fixed list', [('shares_chg1', '>', 5)]),
    ('X.prom_fall_5', RULE + '3', [('prom_chg_1y', '<', -5)]),
    ('X.new_pledge', RULE + '1.1', [('pledge_new_4q', '==', 1)]),
    ('X.cfo_lt04', RULE + '1.4', [('cfo_pat_3y', '<', 0.4)]),
]


# Hypotheses and rules not tested, or tested only in part: kept in patterns.csv so they don't vanish.
NOT_TESTED = [
    ('NT.H3', HYP + 'H3', 'partial (H3.*): no 10-year median, no Consistent/Volatile split, no P/B'),
    ('NT.H5', HYP + 'H5', 'partial (H5.*): tests prior growth among winners, not P(next CAGR | prior CAGR); PAT floor not built'),
    ('NT.H6', HYP + 'H6', 'partial (H6.*): first crossing of 15% in 10+ years and the PAT floor not computable from the features'),
    ('NT.H7', HYP + 'H7', 'partial (H7.*): 3-year PAT CAGR for 2-year; the outcome (reaching the top 100) not measured'),
    ('NT.H9', HYP + 'H9', 'not tested: a decomposition of the run (EPS and P/E change, lag), not a start-date pattern; left to the playbook episode studies (S7)'),
    ('NT.H11', HYP + 'H11', 'not tested: no SUE or results-date returns in the features; q_eps_yoy is only a loose proxy'),
    ('NT.H12', HYP + 'H12', 'partial (H12.*): 12-month return, not 12-1 month; no 6-12 month excess return'),
    ('NT.H13', HYP + 'H13', 'not tested: needs 3x-in-2-years cases and later give-back by ROE, Consistent/Volatile and re-rating share'),
    ('NT.H14', HYP + 'H14', 'partial (X.*): rule 12 triggers tested in exits; drawdown depth and counts during runs not measured'),
    ('NT.H15', HYP + 'H15', 'partial (X.*): signals tested against later falls; excess return after crossing not measured'),
    ('NT.H16', HYP + 'H16', 'partial (H16.*): 3 years for the 10 in the hypothesis'),
    ('NT.H17', HYP + 'H17', 'not tested: economic profit needs net worth, which the features do not carry'),
    ('NT.H18', HYP + 'H18', 'partial (H18.*): 3-year ROE for 10, 52-week high for 5-year, no P/B'),
    ('NT.H20', HYP + 'H20', 'partial (H20.*): CFO/PAT bands only; no CFO/EBITDA quartiles'),
    ('NT.R4', RULE + '4', 'partial (R4.*): gross debt, as the features have no net debt; no current ratio'),
    ('NT.R8', RULE + '8', 'partial (R8.*): trailing P/E; forward earnings were not known at the time'),
]


class Pat:
    def __init__(s, pid, kind, legs, source, h=None, min_mc=None, rule=False, note=''):
        s.id, s.kind, s.legs, s.source, s.h, s.min_mc, s.rule, s.note = pid, kind, legs, source, h, min_mc, rule, note
        s.chart = all(L[0] in CHART for L in legs)
        s.stmt = any(L[0] in STMT for L in legs)
        s.has_pct = any(L[1].startswith('pct') for L in legs)
        s.defn = ' and '.join(f"{L[0]} {L[1]} {' '.join(str(round(x, 3) if isinstance(x, float) else x) for x in L[2:])}" for L in legs) \
            + (f' (mc >= {min_mc})' if min_mc else '')


def make_patterns():
    out = []
    for f in CHART_NUM + STMT_NUM + SHP_NUM:
        out.append(Pat(f'T.{f}.top', 'third', [(f, 'pct>=', 2 / 3)], 'fixed list'))
        out.append(Pat(f'T.{f}.bottom', 'third', [(f, 'pct<=', 1 / 3)], 'fixed list'))
    for f in CHART_BIN + STMT_BIN + SHP_BIN:
        out.append(Pat(f'B.{f}.1', 'binary', [(f, '==', 1)], 'fixed list'))
        out.append(Pat(f'B.{f}.0', 'binary', [(f, '==', 0)], 'fixed list'))
    for f, vals in ATTRS.items():
        out += [Pat(f'A.{f}.{v}', 'attribute', [(f, '==', v)], 'fixed list') for v in vals]
    out += [Pat(f'A.customers.{v}', 'attribute', [('customers', 'has', v)], 'fixed list') for v in CUSTOMERS]
    for pid, src, legs, o in THRESHOLDS:
        out.append(Pat(pid, 'rule' if o.get('rule') else 'threshold', legs, src, o.get('h'), o.get('min_mc'), bool(o.get('rule')), o.get('note', '')))
    return out


def make_exits():
    return [Pat(pid, 'exit', legs, src, ['short', 'medium']) for pid, src, legs in EXIT_SIGNALS]


def list_hash():
    txt = json.dumps(['chart winners: all market, first known window'] + [[p.id, p.defn, p.source, p.h] for p in make_patterns() + make_exits()] +
                     [FREQ_MIN, LIFT_MIN, MIN_TYPE_WINNERS, MIN_KNOWN, MIN_CELL, MIN_DIST, PANEL_DIST, WIN, MIN_MC], sort_keys=True)
    return hashlib.sha1(txt.encode()).hexdigest()[:12]


# --- data ---------------------------------------------------------------------------------------------------------------
def fnum(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def load_artefacts(companies):
    """mb_sample.artefacts and what it calls, lifted from its source: importing mb_sample.py would run it and rewrite
    sample_candidates.csv. Also checks that WIN and MIN_MC still match it."""
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mb_sample.py')
    tree = ast.parse(open(fn, encoding='utf-8').read())
    funcs = {'artefacts', 'history', 'at', 'add_years', 'win_years', 'actions', 'f'}
    names = {'FLOOR_NEAR', 'THIN_VALUE', 'THIN_ZERO', 'STEP', 'MISMATCH', 'GAP_BREAK', 'GAP_WARN', 'STALE', '_hist'}
    keep, seen = [], set()
    h = mmc = None
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in funcs:
            keep.append(n)
            seen.add(n.name)
        elif isinstance(n, ast.Assign):
            tg = [x.id for t in n.targets for x in (t.elts if isinstance(t, ast.Tuple) else [t]) if isinstance(x, ast.Name)]
            if set(tg) & names:
                keep.append(n)
                seen |= set(tg)
            if tg == ['H']:
                h = ast.literal_eval(n.value)
            if tg == ['MIN_MC']:
                mmc = ast.literal_eval(n.value)
    if not (funcs | names) <= seen:
        sys.exit(f'mb_sample.py no longer defines {sorted((funcs | names) - seen)}: update load_artefacts')
    if mmc != MIN_MC or {k: tuple(v[:3]) for k, v in h.items()} != {k: tuple(v[:3]) for k, v in WIN.items()}:
        sys.exit('WIN or MIN_MC differ from mb_sample.py')
    ns = {'bisect': bisect, 'dt': dt, 'json': json, 'os': os, 're': re, 'COMPANIES': companies}
    exec(compile(ast.Module(keep, []), fn, 'exec'), ns)
    return ns


def in_years(d, yrs):
    return yrs[0] <= int(d[:4]) <= yrs[1]


def add_years(d, n):
    y = int(d[:4]) + n
    return f'{y}{d[4:]}' if d[4:] != '-02-29' else f'{y}-02-28'


class Data:
    """Every table limited to starts in years y0..y1 when read, so rows outside can't influence anything computed."""

    def __init__(s, a, y0, y1, need_market=True):
        s.a, s.yrs = a, (y0, y1)
        s.mkt, s.px, s.extra, s.merged, s._dist, s._cell, s.panel_vals, s._type_cell = {}, {}, {}, {}, {}, {}, {}, {}
        s._sets, s.art = {}, {}
        s.has_market_file = False
        s.sample = [r for r in s.csv_rows('sample.csv') if s.ok(r['start'])]
        for r in s.sample:
            r['mc0'] = fnum(r['mc0'])
        if need_market:
            s.load_market()
        s.load_tags()
        for fn in (a.features or 'features.csv').split(','):
            s.load_features(fn)

    def path(s, fn):
        return fn if os.path.dirname(fn) or os.path.exists(fn) and not os.path.exists(os.path.join(s.a.dir, fn)) else os.path.join(s.a.dir, fn)

    def csv_rows(s, fn):
        with open(s.path(fn), encoding='utf-8', newline='') as fh:
            return list(csv.DictReader(fh))

    def ok(s, d):
        return bool(d) and in_years(d, s.yrs)

    def to_row(s, r, into=None):
        row = into or [None] * len(COLS)
        for c in ALL_FEATS:
            if c in r and r[c] not in (None, ''):
                row[IX[c]] = (r[c] if c in TEXT else fnum(r[c]))
        return row

    def load_market(s):
        fn = s.a.market_features or os.path.join(s.a.dir, 'market_features.csv')
        s.has_market_file = os.path.exists(fn)
        if not s.has_market_file:
            print(f'WARNING: {fn} not found: chart features limited to what outcomes.csv holds ({", ".join(OUTCOME_FALLBACK)}; '
                  'pe_rel5 from its looser pe_med5)', file=sys.stderr)
        with open(os.path.join(s.a.dir, 'outcomes.csv'), encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh):
                d = r['start']
                if not s.ok(d):
                    continue
                row = [None] * len(COLS)
                for c in META:
                    row[IX[c]] = fnum(r.get(c))
                row[IX['mcap_cr']] = row[IX['mc0']]
                if not s.has_market_file:
                    for f, oc in OUTCOME_FALLBACK.items():
                        row[IX[f]] = fnum(r.get(oc))
                    pe, med = fnum(r.get('pe0')), fnum(r.get('pe_med5'))
                    row[IX['pe_rel5']] = pe / med if pe and med else None
                s.mkt.setdefault(d, {})[r['sym']] = row
                if row[IX['px0']]:
                    s.px.setdefault(r['sym'], []).append((d, row[IX['px0']]))
        if s.has_market_file:
            with open(fn, encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh):
                    d = (r.get('as_of') or r.get('start') or '')[:10]
                    row = s.mkt.get(d, {}).get(r['sym']) if s.ok(d) else None
                    if row is not None:
                        s.to_row(r, row)
        for v in s.px.values():
            v.sort()
        for d, rows in s.mkt.items():  # same-date derived features
            live = [r for r in rows.values() if r[IX['mc0']] and r[IX['mc0']] >= MIN_MC]
            pes = sorted(r[IX['pe']] for r in live if r[IX['pe']] and r[IX['pe']] > 0)
            med = pes[len(pes) // 2] if len(pes) >= MIN_DIST else None
            mcs = sorted((r[IX['mc0']] for r in rows.values() if r[IX['mc0']]), reverse=True)
            for r in rows.values():
                if med and r[IX['pe']] and r[IX['pe']] > 0:
                    r[IX['pe_rel_mkt']] = r[IX['pe']] / med
                if r[IX['mc0']]:  # rank 1 = largest
                    r[IX['mc_rank']] = bisect.bisect_left([-m for m in mcs], -r[IX['mc0']]) + 1

    def load_features(s, fn, panel=False):
        p = s.path(fn)
        if not os.path.exists(p):
            if fn != 'features.csv' or s.a.features:
                print(f'WARNING: features file {p} not found', file=sys.stderr)
            return 0
        n = 0
        with open(p, encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh):
                d = (r.get('as_of') or r.get('start') or '')[:10]
                if not s.ok(d):
                    continue
                s.extra[(r['sym'], d)] = s.to_row(r, s.extra.get((r['sym'], d)))
                s.merged.pop((r['sym'], d), None)
                if panel:
                    s.panel_vals.setdefault(d, {})[r['sym']] = s.extra[(r['sym'], d)]
                n += 1
        s._dist.clear()
        return n

    def load_tags(s):
        s.tags, s.flagged = {}, set()  # flagged at any date (shell, no real operations, unclear): never a peer or a comparison
        fn = os.path.join(s.a.dir, 'business_types.csv')
        if os.path.exists(fn):
            for r in s.csv_rows('business_types.csv'):
                if r.get('flag'):
                    s.flagged.add(r['sym'])
                else:
                    s.tags.setdefault(r['sym'], []).append((r['as_of'], r['business_type']))
        for f in s.flagged:
            s.tags.pop(f, None)

    def type_of(s, sym, d):
        """The tag nearest in time (a company's type is read at one window start, used at others, as mb_features.py does)."""
        t = s.tags.get(sym)
        if not t:
            return None
        day = lambda x: dt.date.fromisoformat(x)
        return min(t, key=lambda x: abs((day(x[0]) - day(d)).days))[1]

    def get(s, sym, d):
        """Market row with the features-file values filled in: for sample and panel rows only, never comparison cells."""
        k = (sym, d)
        if k not in s.merged:
            m, e = s.mkt.get(d, {}).get(sym), s.extra.get(k)
            if m is None and e is None:
                s.merged[k] = [None] * len(COLS)
            elif e is None or m is None:
                s.merged[k] = m or e
            else:
                s.merged[k] = [x if x is not None else y for x, y in zip(m, e)]
        return s.merged[k]

    # ---- market winners (chart features) ----
    def window_set(s, name, rng):
        """{horizon: {sym: [windows, oldest first]}}: every window meeting the threshold and passing the artefact checks."""
        if name in s._sets:
            return s._sets[name]
        cand = {}
        for d, rows in s.mkt.items():
            if not in_years(d, rng):
                continue
            for sym, r in rows.items():
                if not r[IX['mc0']] or r[IX['mc0']] < MIN_MC:
                    continue
                for hz, (_, thr, last, _) in WIN.items():
                    m = mult(r, hz)
                    if d <= last and m is not None and m >= thr:
                        cand.setdefault(sym, []).append((hz, d, r[IX['mc0']], m, r))
        fn = os.path.join(s.a.dir, f'market_winners_{name}.csv')
        cols = ['sym', 'horizon', 'start', 'mc0', 'multiple', 'ok', 'no_history', 'no_actions', 'fails', 'warnings']
        if s.a.refresh and os.path.exists(fn):
            os.remove(fn)
        saved = list(csv.DictReader(open(fn, encoding='utf-8', newline=''))) if os.path.exists(fn) else []
        done = {x['sym'] for x in saved}
        todo = sorted(set(cand) - done)
        if todo:
            ns = load_artefacts(s.a.companies)
            new = not os.path.exists(fn)
            with open(fn, 'a', newline='', encoding='utf-8') as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                if new:
                    w.writeheader()
                for i, sym in enumerate(todo):
                    scr = os.path.join(s.a.companies, sym, 'scr')
                    nh, na = not os.path.exists(os.path.join(scr, 'history.json')), not os.path.exists(os.path.join(scr, 'corporate_actions.json'))
                    for hz, d, mc, m, r in sorted(cand[sym], key=lambda x: (x[0], x[1])):
                        o = {c: r[IX[c]] for c in META if r[IX[c]] is not None}
                        fails, warns = ns['artefacts'](sym, d, ns['win_years'](hz, o), mc, o, 'winner')
                        row = dict(sym=sym, horizon=hz, start=d, mc0=mc, multiple=m, ok=int(not fails), no_history=int(nh), no_actions=int(na),
                                   fails='; '.join(fails), warnings='; '.join(warns))
                        w.writerow(row)
                        saved.append({k: str(v) for k, v in row.items()})
                    fh.flush()
                    ns['_hist'].clear()  # one company at a time: histories are large
                    if i and i % 200 == 0:
                        print(f'artefact checks {name}: {i}/{len(todo)} companies', flush=True)
        live = {(sym, x[0], x[1]) for sym, v in cand.items() for x in v}
        out = {hz: {} for hz in WIN}
        st = {hz: collections.Counter() for hz in WIN}
        comp = {hz: collections.defaultdict(list) for hz in WIN}
        for x in saved:
            if (x['sym'], x['horizon'], x['start']) not in live:  # a window outcomes.csv no longer has
                continue
            hz, okw = x['horizon'], x['ok'] == '1'
            st[hz]['windows'] += 1
            st[hz]['windows_failed'] += not okw
            comp[hz][x['sym']].append((okw, x['no_history'] == '1', x['no_actions'] == '1'))
            if okw:
                out[hz].setdefault(x['sym'], []).append({'sym': x['sym'], 'start': x['start'], 'mc0': float(x['mc0']), 'horizon': hz,
                                                         'business_type': s.type_of(x['sym'], x['start'])})
        for hz in WIN:
            for v in out[hz].values():
                v.sort(key=lambda w: w['start'])
            c = comp[hz]
            st[hz].update(companies=len(c), companies_lost=sum(not any(y[0] for y in v) for v in c.values()),
                          no_history=sum(v[0][1] for v in c.values()), no_actions=sum(v[0][2] for v in c.values()),
                          no_actions_lost=sum(v[0][2] and not any(y[0] for y in v) for v in c.values()))
        s.art[name] = {hz: dict(sorted(v.items())) for hz, v in st.items()}
        s._sets[name] = out
        return out

    def market_windows(s, hz, yrs):
        out = {}
        for name, rng in (('disc', DISC), ('test', TEST)):
            if rng[0] <= yrs[1] and yrs[0] <= rng[1]:
                if rng[0] < s.yrs[0] or rng[1] > s.yrs[1]:
                    raise SystemExit(f'{name} windows are outside the years loaded {s.yrs}')
                for sym, v in s.window_set(name, rng)[hz].items():
                    out.setdefault(sym, []).extend(v)
        return out

    def chart_winners(s, p, hz, yrs, scope='overall'):
        """(windows, companies): each company once, at its first qualifying window where the pattern can be judged. hit() is
        None only for a missing value or missing same-date distribution, so the choice never depends on the feature's value."""
        ws, total = [], 0
        for sym, wins in sorted(s.market_windows(hz, yrs).items()):
            v = [w for w in wins if (not p.min_mc or w['mc0'] >= p.min_mc) and (scope == 'overall' or w['business_type'] == scope)]
            if not v:
                continue
            total += 1
            w = next((w for w in v if s.hit(p, s.mkt[w['start']][sym], w['start']) is not None), None)
            if w:
                ws.append(w)
        return ws, total

    def scope_winners(s, p, hz, yrs, scope='overall'):
        if p.chart:
            return s.chart_winners(p, hz, yrs, scope)
        ws = [w for w in s.winners(hz, yrs, scope, p) if w['start'] <= WIN[hz][2]]
        return ws, len(ws)

    # ---- evaluating a pattern ----
    def dist(s, d, f):
        k = (d, f)
        if k not in s._dist:
            v = [r[IX[f]] for r in s.mkt.get(d, {}).values() if r[IX[f]] is not None and r[IX['mc0']] and r[IX['mc0']] >= MIN_MC]
            if len(v) < MIN_DIST:
                pv = [r[IX[f]] for r in s.panel_vals.get(d, {}).values() if r[IX[f]] is not None]
                v = pv if len(pv) >= PANEL_DIST else None
            s._dist[k] = sorted(v) if v else None
        return s._dist[k]

    def cut(s, d, f, q, op):
        v = s.dist(d, f)
        if not v:
            return None
        n = len(v)
        return v[min(n - 1, int(math.ceil(q * n)))] if op == 'pct>=' else v[max(0, int(math.floor(q * n)) - 1)]

    def leg(s, L, row, d):
        f, op, a = L[0], L[1], L[2]
        v = row[IX[f]]
        if v is None:
            return None
        if op == 'pct>=' or op == 'pct<=':
            c = s.cut(d, f, a, op)
            return None if c is None else (v >= c if op == 'pct>=' else v <= c)
        if op == 'has':
            return a in v
        if op == '==':
            return v == a
        if op == '!=':
            return v != a
        if op == 'btw':
            return a <= v < L[3]
        return v >= a if op == '>=' else v > a if op == '>' else v <= a if op == '<=' else v < a

    def hit(s, p, row, d):
        """True / False, or None when any leg can't be judged. Strict: a missing leg is unknown, never a pass or a fail."""
        res = True
        for L in p.legs:
            r = s.leg(L, row, d)
            if r is None:
                return None
            res = res and r
        return res

    def comps(s, d, b, hz):
        """Companies below the winner threshold on this date and in this band (mb_sample.py's filters)."""
        k = (d, b, hz)
        if k not in s._cell:
            cols, thr, last, _ = WIN[hz]
            s._cell[k] = [r for r in s.mkt.get(d, {}).values() if d <= last and r[IX['mc0']] and r[IX['mc0']] >= MIN_MC
                          and (b is None or band(r[IX['mc0']]) == b) and (mult(r, hz) is not None and mult(r, hz) < thr)]
        return s._cell[k]

    def winners(s, hz, yrs, scope='overall', p=None):
        out = [w for w in s.sample if w['group'] == 'winner' and w['horizon'] == hz and in_years(w['start'], yrs)
               and w['mc0'] and w['mc0'] >= MIN_MC and (scope == 'overall' or w['business_type'] == scope)]
        return [w for w in out if not p or not p.min_mc or w['mc0'] >= p.min_mc]


def mult(row, hz):
    v = [row[IX[c]] for c in WIN[hz][0] if row[IX[c]] is not None]
    return max(v) if v else None


def rnd(x, n=3):
    return '' if x is None else 'inf' if x == math.inf else round(x, n)


def lift_of(a, b):
    return None if a is None or b is None else (a / b if b else (math.inf if a else None))


def freq_row(D, p, ws):
    known = hits = known_nr = hits_nr = 0
    for w in ws:
        row = D.get(w['sym'], w['start'])
        h = D.hit(p, row, w['start'])
        if h is None:
            continue
        known += 1
        hits += h
        if not row[IX['stmt_gap_fy']]:
            known_nr += 1
            hits_nr += h
    return {'known': known, 'hits': hits, 'freq': hits / known if known else None,
            'freq_nr': hits_nr / known_nr if known_nr else None, 'known_nr': known_nr}


def market_lift(D, p, ws, hz):
    """Winners against all companies below the threshold in the same (date, band), cells weighted by winners."""
    cells = collections.defaultdict(list)
    for w in ws:
        h = D.hit(p, D.get(w['sym'], w['start']), w['start'])
        if h is not None:
            cells[(w['start'], band(w['mc0']))].append(h)
    used = hits = cn = 0
    wsum = 0.0
    n_cells = 0
    for (d, b), hs in cells.items():
        k = c_hit = 0
        for r in D.comps(d, b, hz):
            if p.min_mc and r[IX['mc0']] < p.min_mc:
                continue
            x = D.hit(p, r, d)
            if x is not None:
                k += 1
                c_hit += x
        if k < MIN_CELL:
            continue
        n_cells += 1
        used += len(hs)
        hits += sum(hs)
        cn += k
        wsum += len(hs) * c_hit / k
    if not used:
        return {'used': 0, 'cells': 0, 'comp_n': 0, 'freq': None, 'comp': None, 'lift': None}
    f, c = hits / used, wsum / used
    return {'used': used, 'cells': n_cells, 'comp_n': cn, 'freq': f, 'comp': c, 'lift': lift_of(f, c)}


def split_lift(D, p, ws, hz, key):
    """market_lift within each group of winners (regime or band): {group: figures}."""
    g = collections.defaultdict(list)
    for w in ws:
        g[key(w)].append(w)
    return {k: market_lift(D, p, v, hz) for k, v in sorted(g.items()) if k}


def regime_of(d):
    return next((n for n, a, b in REGIMES if a <= int(d[:4]) <= b), None)


def brief(m):
    return {'n': m['used'], 'freq': rnd(m['freq']), 'comp': rnd(m['comp']), 'lift': rnd(m['lift'])}


def same_type_lift(D, p, ws, hz):
    """Per winner, the share among all same-type tagged companies on its date below the threshold; mean over winners."""
    def peers_of(w):
        k = (w['start'], hz, w['business_type'])
        if k not in D._type_cell:
            D._type_cell[k] = [(sym, r) for sym, r in D.mkt.get(w['start'], {}).items() if sym in D.tags
                               and r[IX['mc0']] and r[IX['mc0']] >= MIN_MC and mult(r, hz) is not None
                               and mult(r, hz) < WIN[hz][1] and w['start'] <= WIN[hz][2]
                               and D.type_of(sym, w['start']) == w['business_type']]
        return [x for x in D._type_cell[k] if x[0] != w['sym']]
    return per_winner_lift(D, p, ws, peers_of)


def per_winner_lift(D, p, ws, peers_of):
    """freq among winners / mean per-winner share among that winner's comparison companies; also by the winner's band, with
    comparison companies in the same band only."""
    tot = [0, 0, 0.0, 0]
    by = collections.defaultdict(lambda: [0, 0, 0.0, 0])
    for w in ws:
        h = D.hit(p, D.get(w['sym'], w['start']), w['start'])
        if h is None:
            continue
        rows = [(r[IX['mc0']], D.hit(p, r, w['start'])) for _, r in peers_of(w)]
        k = [x for _, x in rows if x is not None]
        if k:
            tot[0] += 1
            tot[1] += h
            tot[2] += sum(k) / len(k)
            tot[3] += len(k)
        sb = [x for m, x in rows if x is not None and m and band(m) == band(w['mc0'])]
        if sb:
            e = by[band(w['mc0'])]
            e[0] += 1
            e[1] += h
            e[2] += sum(sb) / len(sb)
            e[3] += len(sb)
    if not tot[0]:
        return {'used': 0, 'comp_n': 0, 'freq': None, 'comp': None, 'lift': None, 'by_band': {}}
    f, c = tot[1] / tot[0], tot[2] / tot[0]
    bb = {b: {'n': e[0], 'peers': e[3], 'freq': rnd(e[1] / e[0]), 'comp': rnd(e[2] / e[0]), 'lift': rnd(lift_of(e[1] / e[0], e[2] / e[0]))}
          for b, e in sorted(by.items())}
    return {'used': tot[0], 'comp_n': tot[3], 'freq': f, 'comp': c, 'lift': lift_of(f, c), 'by_band': bb}


def nearby(p):
    """The pattern with its cut-offs moved (looser and tighter), or [] when there is no number to move."""
    out = []
    for sign, m in ((-1, NEARBY[0]), (1, NEARBY[1])):
        legs, moved = [], False
        for L in p.legs:
            f, op = L[0], L[1]
            if op in ('pct>=', 'pct<='):
                legs.append((f, op, L[2] + sign * PCT_NEARBY))
                moved = True
            elif op in ('>=', '>', '<=', '<') and L[2] != 0:
                legs.append((f, op, L[2] * m))
                moved = True
            elif op == 'btw':
                legs.append((f, op, L[2] * m, L[3] * m))
                moved = True
            else:
                legs.append(L)
        if moved:
            out.append((f'x{m}' if not p.has_pct else f'{sign * PCT_NEARBY:+.3f}',
                        Pat(p.id, p.kind, legs, p.source, p.h, p.min_mc)))
    return out


# --- patterns.csv -------------------------------------------------------------------------------------------------------
FIELDS = ['pattern', 'horizon', 'scope', 'kind', 'data', 'winners_from', 'definition', 'source', 'note', 'stage_failed',
          'done_scan', 'scan_status', 'w_total', 'w_known', 'w_hits', 'freq', 'freq_no_restated', 'w_known_no_restated',
          'market_status', 'm_winners', 'm_cells', 'm_comp_n', 'm_freq', 'm_comp', 'm_lift',
          'done_peers', 'p_status', 'p_winners', 'p_comp_n', 'p_freq', 'p_comp', 'p_lift', 'p_by_band', 'p_group',
          'pair_n', 'pair_freq_w', 'pair_freq_c', 'pair_lift', 'close_n', 'close_freq_w', 'close_freq_c', 'close_lift', 'pair_disagrees',
          'done_test', 't_status', 't_total', 't_known', 't_coverage', 't_freq', 't_winners', 't_comp_n', 't_comp', 't_lift',
          't_type_winners', 't_type_comp', 't_type_lift', 't_type_by_band', 't_regimes', 't_regimes_pass', 't_bands', 't_bands_pass', 't_nearby', 't_fragile',
          'done_wm', 'wm_known', 'wm_pass', 'wm_hits', 'wm_precision', 'wm_base', 'wm_lift', 'wm_med', 'wm_all_med', 'wm_mean', 'wm_all_mean', 'wm_periods',
          'rule_caught', 'rule_missed', 'rule_unknown', 'rule_false_alarms',
          'done_exit', 'ex_status', 'ex_disc', 'ex_test', 'ex_mkt_disc', 'ex_mkt_test']


class Results:
    def __init__(s, a):
        s.a = a
        s.path = a.out or os.path.join(a.dir, 'patterns.csv')
        s.meta_path = os.path.join(os.path.dirname(s.path) or '.', 'patterns_meta.json')
        s.rows = {}
        if os.path.exists(s.path):
            with open(s.path, encoding='utf-8', newline='') as fh:
                for r in csv.DictReader(fh):
                    s.rows[(r['pattern'], r['horizon'], r['scope'])] = r
        s.meta = {}
        if os.path.exists(s.meta_path):
            s.meta = json.load(open(s.meta_path, encoding='utf-8'))
        if s.meta.get('list_hash') and s.meta['list_hash'] != list_hash() and not a.force:
            sys.exit(f"the fixed pattern list or thresholds changed since {s.path} was started (hash {s.meta['list_hash']} -> {list_hash()}): "
                     'the list must be set before the scan. Use a new --out, or --force to mix them knowingly.')

    def base(s, p, hz, scope):
        return s.rows.setdefault((p.id, hz, scope), {
            'pattern': p.id, 'horizon': hz, 'scope': scope, 'kind': p.kind, 'data': 'chart' if p.chart else 'statements/shareholding',
            'winners_from': '' if p.kind == 'exit' else 'market' if p.chart else 'sample',
            'definition': p.defn, 'source': p.source, 'note': p.note, 'stage_failed': ''})

    def save(s):
        tmp = s.path + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction='ignore')
            w.writeheader()
            w.writerows(s.rows.values())
        for attempt in range(10):  # another process can hold the file for a moment
            try:
                os.replace(tmp, s.path)
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(3)
        ps = collections.Counter(r['stage_failed'] or 'alive' for r in s.rows.values())
        tried = [r for r in s.rows.values() if r['kind'] != 'not_tested']
        s.meta.update(list_hash=list_hash(), rows=len(tried), distinct_patterns=len({r['pattern'] for r in tried}), not_tested=len(s.rows) - len(tried),
                      freq_min=FREQ_MIN, lift_min=LIFT_MIN, status=dict(sorted(ps.items())))
        with open(s.meta_path, 'w', encoding='utf-8') as fh:
            json.dump(s.meta, fh, indent=1, sort_keys=True)

    def report(s):
        print(f"patterns tried: {s.meta.get('distinct_patterns')} distinct, {s.meta.get('rows')} pattern x horizon x scope rows -> {s.path}")
        print('status:', s.meta.get('status'))


# --- step 2-3 ------------------------------------------------------------------------------------------------------------
def scan(a):
    D = Data(a, *DISC)  # nothing from 2016 on is even read into memory
    R = Results(a)
    pats = make_patterns()
    for pid, src, why in NOT_TESTED:
        R.rows[(pid, 'all', 'overall')] = {'pattern': pid, 'horizon': 'all', 'scope': 'overall', 'kind': 'not_tested', 'source': src, 'note': why,
                                           'stage_failed': 'not_tested', 'scan_status': why.split(' (')[0].split(':')[0]}
    too_few, by_type = {}, {}
    for hz in WIN:
        types = collections.Counter(w['business_type'] for w in D.winners(hz, DISC))
        mw = D.market_windows(hz, DISC)
        tagged = collections.Counter(t for v in mw.values() for t in {w['business_type'] for w in v} if t)
        by_type[hz] = {'market_winners': len(mw), 'tagged': sum(1 for v in mw.values() if any(w['business_type'] for w in v)),
                       'chart_winners_by_type': dict(sorted(tagged.items())), 'sample_winners_by_type': dict(sorted(types.items()))}
        too_few[hz] = {'chart': {t: n for t, n in sorted(tagged.items()) if n < MIN_TYPE_WINNERS},
                       'sample': {t: n for t, n in sorted(types.items()) if n < MIN_TYPE_WINNERS}}
        chart_sc = {t for t, n in tagged.items() if n >= MIN_TYPE_WINNERS}
        stmt_sc = {t for t, n in types.items() if n >= MIN_TYPE_WINNERS}
        for scope in ['overall'] + sorted(chart_sc | stmt_sc):
            for p in pats:
                if p.h and hz not in p.h:
                    continue
                if scope != 'overall' and scope not in (chart_sc if p.chart else stmt_sc):
                    continue
                r = R.base(p, hz, scope)
                if r.get('done_scan') and not a.force:
                    continue
                r['stage_failed'] = ''
                ws, total = D.scope_winners(p, hz, DISC, scope)
                f = freq_row(D, p, ws)
                r.update(w_total=total, w_known=f['known'], w_hits=f['hits'], freq=rnd(f['freq']), freq_no_restated=rnd(f['freq_nr']),
                         w_known_no_restated=f['known_nr'], market_status='', m_winners='', m_cells='', m_comp_n='', m_freq='', m_comp='', m_lift='')
                if f['known'] < MIN_KNOWN:
                    if p.has_pct and not p.chart:  # no same-date distribution yet: measured in `peers`
                        r.update(scan_status='deferred: no same-date distribution', market_status='skip_to_step4', done_scan=1)
                    elif p.chart and not D.has_market_file and not f['known']:
                        r.update(scan_status='no_market_data', done_scan='')  # retried once market_features.csv exists
                    else:
                        r.update(scan_status='too_few_known', stage_failed='scan_too_few', done_scan=1)
                    continue
                r['done_scan'] = 1
                if f['freq'] < FREQ_MIN:
                    r.update(scan_status='below_freq', stage_failed='scan_freq')
                    continue
                if p.stmt and (f['freq_nr'] is None or f['freq_nr'] < FREQ_MIN):
                    r.update(scan_status='depends_on_restated', stage_failed='restated')
                    continue
                r['scan_status'] = 'kept'
                if not p.chart:
                    r['market_status'] = 'skip_to_step4'
                    continue
                m = market_lift(D, p, ws, hz)
                r.update(m_winners=m['used'], m_cells=m['cells'], m_comp_n=m['comp_n'], m_freq=rnd(m['freq']), m_comp=rnd(m['comp']), m_lift=rnd(m['lift']))
                if m['used'] < MIN_KNOWN:
                    r.update(market_status='too_few_in_cells', stage_failed='market_too_few')
                elif m['lift'] is not None and m['lift'] >= LIFT_MIN:
                    r['market_status'] = 'pass'
                else:
                    r.update(market_status='fail', stage_failed='market_lift')
            R.save()
    R.meta.update(too_few=too_few, winners_by_type=by_type, discovery_sample_winners={hz: len(D.winners(hz, DISC)) for hz in WIN},
                  artefact_check_disc=D.art.get('disc'))
    R.save()
    for hz, t in by_type.items():
        print(f"{hz}: market winners {t['market_winners']}, tagged {t['tagged']}; artefacts {D.art['disc'][hz]}")
        print(f'  chart winners by type (<{MIN_TYPE_WINNERS} = too few):', ', '.join(f'{k} {v}' for k, v in t['chart_winners_by_type'].items()) or '-')
        print('  sample winners too few:', ', '.join(f'{k} {v}' for k, v in too_few[hz]['sample'].items()) or '-')
    R.report()


# --- step 4: the panel ---------------------------------------------------------------------------------------------------
def industry(a, sym, cache={}):
    if sym not in cache:
        cache[sym] = None
        fn = os.path.join(a.companies, sym, 'scr', 'overview.json')
        try:
            s = [x for x in json.load(open(fn, encoding='utf-8'))['data'].get('sectors') or [] if x]
            cache[sym] = s[-1] if s else None
        except (OSError, ValueError, KeyError, AttributeError, TypeError):
            pass
    return cache[sym]


def panel(a):
    D = Data(a, *DISC)
    fn = os.path.join(a.dir, 'peer_panel.csv')
    old = collections.defaultdict(list)
    if os.path.exists(fn):
        for r in csv.DictReader(open(fn, encoding='utf-8', newline='')):
            old[(r['for_winner'], r['horizon'], r['start'])].append(r)
    out, dropped, short = [], 0, []
    for hz in WIN:
        for w in D.winners(hz, DISC):
            sym, d, typ = w['sym'], w['start'], w['business_type']
            key = (sym, hz, d)
            kept = []
            for r in old.get(key, []):
                t = D.type_of(r['sym'], d)
                if r['sym'] in D.flagged:
                    dropped += 1
                elif t == typ:
                    kept.append(dict(r, source='tagged'))
                elif t is None:
                    kept.append(dict(r, source='untagged'))
                else:
                    dropped += 1  # tagged since as another type: replaced from the same seeded order
            have = {r['sym'] for r in kept} | {x['sym'] for x in old.get(key, [])}
            rng = random.Random(f'{a.seed}|{sym}|{hz}|{d}')
            live = sorted(s for s, r in D.mkt.get(d, {}).items() if s != sym and s not in have and s not in D.flagged and r[IX['mc0']] and r[IX['mc0']] >= MIN_MC
                          and mult(r, hz) is not None and mult(r, hz) < WIN[hz][1])
            rng.shuffle(live)  # random across all size bands; nothing about looking similar
            tagged = [s for s in live if D.type_of(s, d) == typ]
            ind = industry(a, sym)
            untagged = [s for s in live if not D.tags.get(s) and ind and industry(a, s) == ind] if len(kept) + len(tagged) < a.n else []
            for s in (tagged + untagged)[:max(0, a.n - len(kept))]:
                kept.append({'sym': s, 'as_of': d, 'start': d, 'group': 'peer', 'for_winner': sym, 'horizon': hz, 'business_type': typ,
                             'source': 'tagged' if s in tagged else 'untagged', 'mc0': D.mkt[d][s][IX['mc0']], 'size_band': band(D.mkt[d][s][IX['mc0']])})
            if len(kept) < a.n:
                short.append(f'{sym} {hz} {d} ({typ}): {len(kept)}')
            out += kept
    cols = ['sym', 'as_of', 'start', 'group', 'for_winner', 'horizon', 'business_type', 'source', 'mc0', 'size_band']
    with open(fn, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    need = {}
    for r in out:
        if r['source'] == 'untagged':
            e = need.setdefault((r['sym'], r['as_of']), set())
            e.add(f"{r['for_winner']} {r['horizon']}")
    un = os.path.join(a.dir, 'peer_untagged.csv')
    with open(un, 'w', newline='', encoding='utf-8') as fh:  # the columns of needs_next.csv, for tagging and for --rows
        w = csv.writer(fh)
        w.writerow(['sym', 'as_of', 'groups', 'for_winner', 'status'])
        for (s, d), e in sorted(need.items()):
            w.writerow([s, d, 'peer', ';'.join(sorted(e)), 'untagged'])
    print(f'{fn}: {len(out)} rows, {len({r["sym"] for r in out})} companies; untagged {len(need)} -> {un}; '
          f'replaced after tagging as another type {dropped}; winners with fewer than {a.n} peers {len(short)}')
    print('by band:', dict(collections.Counter(r['size_band'] for r in out)))
    for s in short[:40]:
        print('  short:', s)
    print('next: tag peer_untagged.csv (business-type tagging, process/s6_playbook.md); re-run panel until none is untagged; then mb_features.py --rows peer_panel.csv '
          '--out features_panel.csv; bse_shp.py --rows peer_panel.csv; ar_statements.py plan --rows peer_panel.csv --groups peer')


# --- step 4-5: scoring ---------------------------------------------------------------------------------------------------
def pair_lift(D, p, pairs):
    n = hw = hc = 0
    for w, c in pairs:
        a_, b_ = D.hit(p, D.get(w['sym'], w['start']), w['start']), D.hit(p, D.get(c, w['start']), w['start'])
        if a_ is None or b_ is None:
            continue
        n += 1
        hw += a_
        hc += b_
    return (n, hw / n, hc / n, lift_of(hw / n, hc / n)) if n else (0, None, None, None)


def peers(a):
    D = Data(a, *DISC)
    R = Results(a)
    if not R.rows:
        sys.exit('no patterns.csv: run scan first')
    pf = os.path.join(a.dir, 'peer_panel.csv')
    if not os.path.exists(pf):
        sys.exit('no peer_panel.csv: run panel first')
    plist = [r for r in csv.DictReader(open(pf, encoding='utf-8', newline='')) if in_years(r['start'], DISC)]
    D.load_features(a.panel_features or 'features_panel.csv', panel=True)
    by = collections.defaultdict(list)
    for r in plist:  # only peers confirmed as the winner's type; an untagged draw isn't one yet
        if D.type_of(r['sym'], r['start']) == r['business_type']:
            by[(r['for_winner'], r['horizon'], r['start'])].append(r['sym'])
    pats = {p.id: p for p in make_patterns()}
    waiting = 0
    for k, r in R.rows.items():
        p = pats.get(k[0])
        if not p or r['stage_failed'] or not r.get('done_scan') or (r.get('done_peers') and not a.force):
            continue
        hz, scope = k[1], k[2]
        ws = D.winners(hz, DISC, scope, p)
        f = freq_row(D, p, ws)
        if r.get('scan_status', '').startswith('deferred'):  # thirds of a statement feature: now against the panel's cut-offs
            r.update(w_known=f['known'], w_hits=f['hits'], freq=rnd(f['freq']), freq_no_restated=rnd(f['freq_nr']), w_known_no_restated=f['known_nr'])
            if f['known'] < MIN_KNOWN:
                r['p_status'] = 'waiting: no panel features or too few on each date'
                waiting += 1
                continue
            if f['freq'] < FREQ_MIN:
                r.update(scan_status='below_freq (panel cut-offs)', stage_failed='scan_freq', done_peers=1, p_status='')
                continue
            if p.stmt and (f['freq_nr'] is None or f['freq_nr'] < FREQ_MIN):
                r.update(scan_status='depends_on_restated', stage_failed='restated', done_peers=1, p_status='')
                continue
        if p.chart:
            m = same_type_lift(D, p, [w for w in D.chart_winners(p, hz, DISC, scope)[0] if w['business_type']], hz)
            group = 'all same-type companies; tagged market winners'
        else:
            m = per_winner_lift(D, p, ws, lambda w: [(s, D.get(s, w['start'])) for s in by.get((w['sym'], hz, w['start']), [])])
            group = 'peer_panel.csv'
        r.update(p_group=group, p_winners=m['used'], p_comp_n=m['comp_n'], p_freq=rnd(m['freq']), p_comp=rnd(m['comp']), p_lift=rnd(m['lift']),
                 p_by_band=json.dumps(m['by_band'], sort_keys=True))
        if m['used'] < MIN_KNOWN:
            r['p_status'] = 'waiting: too few winners with known peers'
            waiting += 1
            continue
        passed = m['lift'] is not None and m['lift'] >= LIFT_MIN
        r['p_status'] = 'pass' if passed else 'fail'
        r['done_peers'] = 1
        if not passed:
            r['stage_failed'] = 'peer_lift'
        # step 5: frozen pairs, all and close-size; reported, never averaged in
        pairs = [(w, w['control'], w.get('size_step')) for w in ws if w.get('control')]
        n, fw, fc, lf = pair_lift(D, p, [(w, c) for w, c, _ in pairs])
        nc, fwc, fcc, lc = pair_lift(D, p, [(w, c) for w, c, st in pairs if st == CLOSE_STEP])
        r.update(pair_n=n, pair_freq_w=rnd(fw), pair_freq_c=rnd(fc), pair_lift=rnd(lf), close_n=nc, close_freq_w=rnd(fwc), close_freq_c=rnd(fcc), close_lift=rnd(lc))
        ref = m['lift']
        dis = []
        for nm, x, nn in (('pairs', lf, n), ('close', lc, nc)):
            if x is not None and ref and nn >= MIN_CELL and ((x >= LIFT_MIN) != (ref >= LIFT_MIN)):
                dis.append(nm)
        r['pair_disagrees'] = ';'.join(dis)
    R.save()
    if waiting:
        print(f'{waiting} rows wait for peer data (features_panel.csv or tags); re-run after the fetch')
    R.report()


# --- market_fetch.txt ----------------------------------------------------------------------------------------------------
def market_fetch(a):
    R = Results(a)
    alive = [r for r in R.rows.values() if not r['stage_failed'] and r.get('data', '').startswith('statements') and r.get('done_peers')]
    if not alive and not a.force:
        print('no pattern using statements has reached the out-of-sample stage: nothing written (--force to write anyway)')
        return
    syms = set()
    with open(os.path.join(a.dir, 'outcomes.csv'), encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            mc = fnum(r.get('mc0'))
            if mc and mc >= MIN_MC and in_years(r['start'], TEST):
                syms.add(r['sym'])
    missing = sorted(s for s in syms if not any(os.path.exists(os.path.join(a.companies, s, 'scr', f))
                                                for f in ('profit_loss.json', 'profit_loss_standalone.json')))
    fn = os.path.join(a.dir, 'market_fetch.txt')
    with open(fn, 'w', encoding='utf-8') as fh:
        fh.writelines(s + '\n' for s in missing)
    print(f'{fn}: {len(missing)} companies without saved statements, of {len(syms)} with a start market cap >= {MIN_MC} cr in 2016-2023; '
          f'{len(alive)} surviving rows use statements')


# --- step 6-7 ------------------------------------------------------------------------------------------------------------
def whole_market(D, p, hz, scope, tag_needs, tag_limit, seed):
    thr, last = WIN[hz][1], WIN[hz][2]
    tot = {k: [0, 0, 0, [], []] for k in ('disc', 'test')}  # known, passed, passed winners, multiples of passed, of all
    need = []
    for d in sorted(D.mkt):
        if d > last or not in_years(d, (DISC[0], TEST[1])):
            continue
        t = tot['disc' if in_years(d, DISC) else 'test']
        for sym, r in D.mkt[d].items():
            if not r[IX['mc0']] or r[IX['mc0']] < MIN_MC or (p.min_mc and r[IX['mc0']] < p.min_mc):
                continue
            m = mult(r, hz)
            if m is None:
                continue
            h = D.hit(p, r, d)
            if h is None:
                continue
            if scope != 'overall':
                ty = D.type_of(sym, d)
                if ty is None:
                    if h:
                        need.append((sym, d))
                    continue
                if ty != scope:
                    continue
            t[0] += 1
            t[4].append(m)
            if h:
                t[1] += 1
                t[2] += m >= thr
                t[3].append(m)
    if scope != 'overall' and need:
        rng = random.Random(f'{seed}|{p.id}|{hz}|{scope}')
        rng.shuffle(need)
        for sym, d in need[:tag_limit]:
            tag_needs.setdefault((sym, d), set()).add(f'{p.id} {hz} {scope}')
    fig = lambda v: {'known': v[0], 'passed': v[1], 'hits': v[2], 'precision': rnd(v[2] / v[1]) if v[1] else '',
                     'median': rnd(statistics.median(v[3])) if v[3] else '', 'mean': rnd(statistics.mean(v[3])) if v[3] else '',
                     'all_median': rnd(statistics.median(v[4])) if v[4] else '', 'all_mean': rnd(statistics.mean(v[4])) if v[4] else ''}
    both = [tot['disc'][i] + tot['test'][i] for i in range(5)]
    base_hits = sum(1 for x in both[4] if x >= thr)
    base = base_hits / both[0] if both[0] else None
    prec = both[2] / both[1] if both[1] else None
    return {'all': fig(both), 'periods': {k: fig(v) for k, v in tot.items()}, 'base': base, 'precision': prec, 'lift': lift_of(prec, base),
            'untagged_passers': len(need)}


def market_has(D, p):
    """The market table holds this pattern's statement or shareholding features on test dates (the full --market run)."""
    fs = [L[0] for L in p.legs if L[0] not in CHART]
    return all(any(r[IX[f]] is not None for d, rows in D.mkt.items() if in_years(d, TEST) for r in rows.values()) for f in fs)


def test(a):
    D = Data(a, DISC[0], TEST[1])
    R = Results(a)
    if not R.rows:
        sys.exit('no patterns.csv: run scan first')
    pats = {p.id: p for p in make_patterns()}
    tag_needs, waiting = {}, 0
    for k, r in R.rows.items():
        p = pats.get(k[0])
        if not p:
            continue
        hz, scope = k[1], k[2]
        last = WIN[hz][2]
        alive = not r['stage_failed'] and r.get('done_peers')
        if alive and (not r.get('done_test') or a.force):
            ws, total = D.scope_winners(p, hz, TEST, scope)
            f = freq_row(D, p, ws)
            m = market_lift(D, p, ws, hz)
            ty = same_type_lift(D, p, [w for w in ws if w['business_type']], hz)
            all_w = D.scope_winners(p, hz, DISC, scope)[0] + ws  # a company counts once in each set
            regs = split_lift(D, p, all_w, hz, lambda w: regime_of(w['start']))
            bds = split_lift(D, p, ws, hz, lambda w: band(w['mc0']))
            ok = lambda x: x['used'] >= MIN_CELL and x['lift'] is not None and x['lift'] >= LIFT_MIN
            test_regs = [n for n, a0, b0 in REGIMES if a0 >= TEST[0] and n in regs and ok(regs[n])]
            near = {lab: brief(market_lift(D, q, ws, hz)) for lab, q in nearby(p)}
            fragile = any(v['lift'] in ('', None) or v['lift'] != 'inf' and v['lift'] < LIFT_MIN for v in near.values())
            r.update(t_total=total, t_known=f['known'], t_coverage=rnd(f['known'] / total) if total else '', t_freq=rnd(f['freq']),
                     t_winners=m['used'], t_comp_n=m['comp_n'], t_comp=rnd(m['comp']), t_lift=rnd(m['lift']),
                     t_type_winners=ty['used'], t_type_comp=rnd(ty['comp']), t_type_lift=rnd(ty['lift']), t_type_by_band=json.dumps(ty['by_band'], sort_keys=True),
                     t_regimes=json.dumps({n: brief(v) for n, v in regs.items()}, sort_keys=True), t_regimes_pass=sum(ok(v) for v in regs.values()),
                     t_bands=json.dumps({n: brief(v) for n, v in bds.items()}, sort_keys=True), t_bands_pass=sum(ok(v) for v in bds.values()),
                     t_nearby=json.dumps(near, sort_keys=True), t_fragile=int(fragile))
            if f['known'] < MIN_KNOWN or m['used'] < MIN_KNOWN:
                if not p.chart and not market_has(D, p):
                    r['t_status'] = 'waiting: market statements (market_fetch.txt, then mb_features.py --market)'
                    waiting += 1
                    continue
                r.update(t_status='too_few', stage_failed='test_too_few', done_test=1)
            else:
                r['done_test'] = 1
                fail = 'test_freq' if f['freq'] < FREQ_MIN else 'test_lift' if not ok(m) else \
                    'test_type_lift' if ty['used'] >= MIN_CELL and (ty['lift'] is None or ty['lift'] < LIFT_MIN) else \
                    'test_regime' if int(r['t_regimes_pass']) < 2 or not test_regs else \
                    'test_band' if int(r['t_bands_pass']) < 2 else 'test_nearby' if fragile else ''
                r.update(t_status='fail' if fail else 'pass', stage_failed=fail)
        # step 7: survivors and every current rule, passed or not (a rule's misses and false alarms are the result)
        if (p.rule or (not r['stage_failed'] and r.get('done_test'))) and (not r.get('done_wm') or a.force) and r.get('done_scan'):
            wm = whole_market(D, p, hz, scope, tag_needs, a.tag_limit, a.seed)
            al = wm['all']
            r.update(wm_known=al['known'], wm_pass=al['passed'], wm_hits=al['hits'], wm_precision=al['precision'], wm_base=rnd(wm['base']), wm_lift=rnd(wm['lift']),
                     wm_med=al['median'], wm_all_med=al['all_median'], wm_mean=al['mean'], wm_all_mean=al['all_mean'],
                     wm_periods=json.dumps(wm['periods'], sort_keys=True))
            if al['known']:
                r['done_wm'] = 1
            if p.rule:
                ws, total = D.scope_winners(p, hz, (DISC[0], TEST[1]), scope)  # each company once across both sets
                hs = [D.hit(p, D.get(w['sym'], w['start']), w['start']) for w in ws]
                r.update(rule_caught=sum(1 for h in hs if h is True), rule_missed=sum(1 for h in hs if h is False),
                         rule_unknown=total - sum(1 for h in hs if h is not None), rule_false_alarms=al['passed'] - al['hits'] if al['known'] else '')
            if not p.rule and al['known'] and not r['stage_failed'] and (wm['lift'] is None or wm['lift'] <= 1):
                r['stage_failed'] = 'whole_market'
    R.meta['artefact_check_test'] = D.art.get('test')
    R.save()
    if tag_needs:
        fn = os.path.join(a.dir, 'type_tag_needs.csv')
        with open(fn, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['sym', 'as_of', 'groups', 'for_winner', 'status'])
            for (s, d), e in sorted(tag_needs.items()):
                w.writerow([s, d, 'type_pattern', ';'.join(sorted(e)), 'untagged'])
        print(f'{fn}: {len(tag_needs)} companies a business-type pattern passes, untagged: tag them (business-type tagging, process/s6_playbook.md) and re-run with --force for precision within the type')
    if waiting:
        print(f'{waiting} rows wait for market statements')
    R.report()


# --- step 8 --------------------------------------------------------------------------------------------------------------
def exit_cases(D):
    """(group, sym, horizon, start, [quarter-ends from first reaching the threshold to the window's end])."""
    cases, dropped = [], 0
    for w in D.sample:
        hz = w['horizon']
        if w['group'] not in ('winner', 'fallen_winner') or hz not in ('short', 'medium'):
            continue
        sym, st = w['sym'], w['start']
        row = D.mkt.get(st, {}).get(sym)
        ser = D.px.get(sym)
        if not row or not ser or not row[IX['px0']]:
            dropped += 1
            continue
        cols, thr, _, yrs = WIN[hz]
        end = add_years(st, yrs)
        qs = [(d, p) for d, p in ser if st < d <= end]
        i = next((j for j, (d, p) in enumerate(qs) if p / row[IX['px0']] >= thr), None)
        if i is None:  # the threshold was reached only between quarter-ends
            dropped += 1
            continue
        pk, e = row[IX[f'pxpeak_{yrs}y']], row[IX[f'px_{yrs}y']]
        fell = pk is not None and e is not None and pk >= thr and e <= pk / 2
        if w['group'] == 'winner' and fell:
            continue
        cases.append(('fallen' if w['group'] == 'fallen_winner' else 'held', sym, hz, st, [d for d, _ in qs[i:]]))
    return cases, dropped


def fall_labels(D):
    """{(sym, d): True if a later quarter-end price within FALL_YEARS is at or below (1 - FALL) x today's; False if the whole
    span is seen without one; None if the span isn't complete."""
    out = {}
    for sym, ser in D.px.items():
        ds = [d for d, _ in ser]
        for i, (d, p) in enumerate(ser):
            end = add_years(d, FALL_YEARS)
            j = bisect.bisect_right(ds, end)
            fell = any(x[1] <= p * (1 - FALL) for x in ser[i + 1:j])
            complete = j < len(ds) or (ds and ds[-1] >= end)
            out[(sym, d)] = True if fell else False if complete else None
    return out


def exit_group_lift(D, p, cases):
    g = {'fallen': [], 'held': []}
    ever = {'fallen': [], 'held': []}
    quarters = 0
    for grp, sym, _, _, qs in cases:
        hs = [D.hit(p, D.get(sym, d), d) for d in qs]
        hs = [h for h in hs if h is not None]
        if hs:
            g[grp].append(sum(hs) / len(hs))
            ever[grp].append(any(hs))
            quarters += len(hs)
    f, h = (statistics.mean(g[k]) if g[k] else None for k in ('fallen', 'held'))
    return {'fallen_n': len(g['fallen']), 'held_n': len(g['held']), 'quarters': quarters, 'fallen_share': rnd(f), 'held_share': rnd(h), 'lift': lift_of(f, h),
            'fallen_ever': rnd(sum(ever['fallen']) / len(ever['fallen'])) if ever['fallen'] else '',
            'held_ever': rnd(sum(ever['held']) / len(ever['held'])) if ever['held'] else ''}


def exit_market(D, p, labels, yrs):
    """How often the signal was followed by a fall, against all companies in the same (date, band) at the signal's weight."""
    sig = fell = 0
    exp = 0.0
    for d, rows in D.mkt.items():
        if not in_years(d, yrs):
            continue
        cells = collections.defaultdict(lambda: [0, 0, 0, 0])  # known, fell, signal, signal and fell
        for sym, r in rows.items():
            l = labels.get((sym, d))
            if l is None or not r[IX['mc0']] or r[IX['mc0']] < MIN_MC:
                continue
            c = cells[band(r[IX['mc0']])]
            h = D.hit(p, r, d)
            if h is None:
                continue
            c[0] += 1
            c[1] += l
            if h:
                c[2] += 1
                c[3] += l
        for c in cells.values():
            if c[2] and c[0]:
                sig += c[2]
                fell += c[3]
                exp += c[2] * c[1] / c[0]
    rate, base = (fell / sig, exp / sig) if sig else (None, None)
    return {'signals': sig, 'fell': fell, 'rate': rnd(rate), 'base': rnd(base), 'lift': lift_of(rate, base)}


def jsn(d):
    return json.dumps({k: (rnd(v) if k == 'lift' else v) for k, v in d.items()}, sort_keys=True)


def exits(a):
    D = Data(a, DISC[0], 2100)
    cases, dropped = exit_cases(D)
    if a.write_rows:
        fn = os.path.join(a.dir, 'exit_rows.csv')
        with open(fn, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['sym', 'as_of', 'group', 'horizon'])
            for k in sorted({(c[1], d, c[0], c[2]) for c in cases for d in c[4]}):
                w.writerow(k)
        print(f'{fn}: quarter-ends for mb_features.py --rows (statement signals); then exits --exit-features FILE')
        return
    if a.exit_features:
        D.load_features(a.exit_features)
    R = Results(a)
    labels = fall_labels(D)
    print(f'{len(cases)} cases ({sum(c[0] == "fallen" for c in cases)} fallen, {sum(c[0] == "held" for c in cases)} held up); '
          f'{dropped} dropped (no price series, or the threshold reached only between quarter-ends)')
    for p in make_exits():
        for hz in p.h:
            r = R.base(p, hz, 'overall')
            if r.get('done_exit') and not a.force:
                continue
            cs = [c for c in cases if c[2] == hz]
            dg, tg = (exit_group_lift(D, p, [c for c in cs if in_years(c[3], y)]) for y in (DISC, TEST))
            dm, tm = (exit_market(D, p, labels, y) for y in (DISC, TEST))
            r.update(ex_disc=jsn(dg), ex_test=jsn(tg), ex_mkt_disc=jsn(dm), ex_mkt_test=jsn(tm), stage_failed='')
            if dg['fallen_n'] < MIN_KNOWN or dg['held_n'] < MIN_KNOWN or not dm['signals']:
                r['ex_status'] = 'waiting: too few cases or no data (statement signals need --exit-features)'
                continue
            r['done_exit'] = 1
            ok = lambda x: x['lift'] is not None and x['lift'] >= LIFT_MIN
            fail = 'exit_groups' if not ok(dg) else 'exit_market' if not ok(dm) else \
                'exit_test_groups' if tg['fallen_n'] < MIN_CELL or not ok(tg) else 'exit_test_market' if not ok(tm) else ''
            r.update(ex_status='fail' if fail else 'pass', stage_failed=fail)
    R.save()
    R.report()


def main():
    ap = argparse.ArgumentParser(description='Study and playbook pattern tests (process/s6_playbook.md)')
    ap.add_argument('cmd', choices=['scan', 'panel', 'peers', 'market_fetch', 'test', 'exits'])
    ap.add_argument('--dir', help='read and write there, not the newest study run')
    ap.add_argument('--out', help='patterns.csv path')
    ap.add_argument('--features', help='features file(s), comma-separated; default features.csv')
    ap.add_argument('--market-features', dest='market_features')
    ap.add_argument('--panel-features', dest='panel_features')
    ap.add_argument('--exit-features', dest='exit_features')
    ap.add_argument('--companies', default=os.path.join('data', 'companies'))
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--n', type=int, default=N_PEERS)
    ap.add_argument('--tag-limit', dest='tag_limit', type=int, default=TAG_LIMIT)
    ap.add_argument('--write-rows', dest='write_rows', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--refresh', action='store_true', help='redo the artefact checks of market winners')
    a = ap.parse_args()
    a.dir = a.dir or hist_dir()
    {'scan': scan, 'panel': panel, 'peers': peers, 'market_fetch': market_fetch, 'test': test, 'exits': exits}[a.cmd](a)


if __name__ == '__main__':
    main()
