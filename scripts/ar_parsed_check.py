"""Annual-report statements (workflow/ar_statements.md): checks the annual-report values that reach the features: every report's final values
(parsed after the subagent override, as ar_statements.load_ar reads them). Read-only: no network, no tokens, changes no
shared file but the flags file.
  python -I scripts/ar_parsed_check.py [--syms A,B] [--raw] [--out FILE] [--test] [--comp DIR]
Writes ar_parsed_flags.csv in the playbook base data folder (or --out FILE): sym, fy, basis, year, field, value, check, detail. detail starts '[used]' when this value
reaches the features (load_ar picks this report for the year and screener lacks the year), else '[unused]'.
--raw: the parser's own values, with subagent files ignored and held-back fields included (to test the checks against faults
subagents have already corrected, and to compare a parser fix). --test: the known faults, caught or missed, in both modes,
and how often each check fires on years a subagent read and found right, against years where it found the parser wrong (the
false-positive rate); writes nothing. --comp DIR: reports from another tree, as a parser test writes them (<DIR>/<SYM>/FY*Q4/
ar_FY*.json with pages_real, and the subagent file beside it): the flags a parser fix would leave, before anything is reparsed.
Checks:
  cfo_sign        the operating cash flow line on the page: 'used in' printed in brackets is an outflow; or a sign that only
                  the opposite of makes operating + investing + financing = the net change
  pbt_tax_pat     pbt - tax != pat
  bs_identity     equity + reserves + borrowings above total assets, or under 10% of them (not banks)
  internal_scale  one basis-year's amounts far apart (over 5x the larger of sales and assets; sales and assets 300x apart);
                  total assets of zero
  unit_mismatch   the balance sheet and P&L of one basis read in different units
  cross_scale / cross_value / cross_sign   the same year in another report: off by a power of ten / by over 50% / sign
  year_scale      neighbouring years, in any report, off by 100x or more in two or more fields
  scr_scale / scr_value / scr_sign         screener's saved statements for the year (same basis)
  chart_scale / chart_value                sales against the chart's TTM sales (no basis within 2x)
  entity          a statement page headed by another company
  page_head / page_far / page_earlier   the page isn't headed as the statement; the balance sheet and P&L are far apart; an
                  earlier adjacent pair of statement pages exists (subsidiaries' accounts follow the company's)
  unit_missing    no unit word on the statements (figures unscaled)
  comma_decimal   figures end in ',dd' (845,65): an OCR comma for the decimal point, so the printed unit can't be trusted
  equity_pref     equity_cap = equity + preference capital by the capital schedule
  year_end        the report's year end isn't the date on the statement pages used
  year_label      a previous-year column labelled 12 months before a year that isn't 12 months long
"""
import argparse, collections, csv, datetime as dt, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ar_statements as A
from config import playbook_dir

COLS = ['sym', 'fy', 'basis', 'year', 'field', 'value', 'check', 'detail']
FEATURE_FIELDS = set(A.FIELDS)  # mb_features.add_ar: every field feeds a feature (dep, interest, other_income through op / ROCE)
SCR = {'profit_loss': {'sales': ('Sales', 'Revenue'), 'pat': ('Net Profit',), 'pbt': ('Profit before tax',)},
       'balance_sheet': {'equity_cap': ('Equity Capital',), 'reserves': ('Reserves',), 'borrowings': ('Borrowings', 'Borrowing'),
                         'total_assets': ('Total Assets',)},
       'cash_flow': {'cfo': ('Cash from Operating Activity',)}}
CROSS = ('sales', 'pbt', 'pat', 'equity_cap', 'reserves', 'borrowings', 'total_assets', 'cfo')
MON = dict(zip('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), range(1, 13)))


def pw(q, tol=0.2):
    """n when q is within tol of 10^n (n != 0); 0 when it's within 25% of 1; else None."""
    if 0.8 <= q <= 1.25:
        return 0
    return next((n for n in range(-7, 8) if n and abs(q * 10.0 ** -n - 1) < tol), None)


def report_list(D, syms=None, comp=None):
    """(sym, json path) of every report with a saved parse; ar_status.csv lists them (no folder scan)."""
    seen, out = set(), []
    if comp:
        for jf in glob.glob(os.path.join(comp, '*', 'FY*Q4', 'ar_FY??.json')):
            sym = os.path.basename(os.path.dirname(os.path.dirname(jf)))
            if not syms or sym in syms:
                out.append((sym, jf))
        return out
    for r in csv.DictReader(open(os.path.join(D, 'ar_status.csv'), encoding='utf-8')):
        jf = r.get('json_file')
        if jf and jf not in seen and (not syms or r['sym'] in syms) and os.path.exists(jf):
            seen.add(jf)
            out.append((r['sym'], jf))
    return out


def values(r, hp, raw):
    """{basis: {year: {field: (value, source)}}}: source 'helper' or the parsed page id."""
    out = {}
    if raw:
        for b, B in (r.get('bases') or {}).items():
            out[b] = {k: {f: (v[0], v[2]) for f, v in y['fields'].items()} for k, y in B['years'].items()
                      if re.match(r'\d{4}-\d\d$', k)}
        return out
    for b, k, f, _ in A.report_final(r, hp):
        py = ((r.get('bases') or {}).get(b) or {}).get('years', {}).get(k, {}).get('fields', {})
        out.setdefault(b, {})[k] = {n: (v[0], 'helper' if v[1] in ('helper', 'derived') else (py.get(n) or [0, 0, ''])[2]) for n, v in f.items()}
    return out


def scr_table(sym, st, basis):
    d = A.load(os.path.join(A.COMP, sym, 'scr', st + ('.json' if basis == 'consolidated' else '_standalone.json'))) or {}
    d = d.get('data') or {}
    out = {}
    for j, y in enumerate(d.get('years') or []):
        m = re.match(r'([A-Z][a-z]{2}) (\d{4})', str(y))
        if m:
            k = f'{m.group(2)}-{MON[m.group(1)]:02d}'
            out[k] = {row.get('label'): (row.get('values')[j] if j < len(row.get('values') or []) else None)
                      for row in d.get('rows') or []}
    return out


def num(x):
    try:
        return float(str(x).replace(',', '').replace('%', ''))
    except (TypeError, ValueError):
        return None


def cf_lines(text):
    """Printed figures of a cash flow page: {'cfo': (label, [current, previous]), 'cfi': ..., 'cff': ..., 'net': ...}."""
    lines = text.splitlines()
    cols = A.columns(lines)
    mid = A.split_at(lines, cols)
    out = {}
    for l in lines:
        tk = A.value_tokens(l, cols)
        if not tk:
            continue
        label = A.clean_label(A.strip_section(l[:tk[0][1]]))
        if not label or re.search(r'before|continuing|discontinu', label):
            continue
        cur = [A.val(t) for t, s, e in tk if mid is None or e <= mid]
        prv = [A.val(t) for t, s, e in tk if mid is not None and e > mid]
        if mid is None and len(cur) == 2:
            cur, prv = cur[:1], cur[1:]
        pair = [cur[-1] if cur else None, prv[-1] if prv else None]
        if re.search(A.F['cf'][0][1], label):
            out['cfo'] = (label, pair)
        elif re.search(r'net cash.*investing|investing activit.*\(b\)|cash.*(used in|from).*investing activit', label):
            out['cfi'] = (label, pair)
        elif re.search(r'net cash.*financing|financing activit.*\(c\)|cash.*(used in|from).*financing activit', label):
            out['cff'] = (label, pair)
        elif re.search(r'net (increase|decrease|change|\(decrease\)|\(increase\))', label):
            out.setdefault('net', (label, pair))
    return out


def own_name(pm):
    """The name most statement pages of this report carry (a company renamed since)."""
    c = collections.Counter(A.entity(t) for t in pm.values() if any(A.stmt_head(t, s) for s in A.HEAD))
    c.pop(None, None)
    return c.most_common(1)[0][0] if c else None


def page_notes(sym, B, b, pm, cname):
    """Basis-level findings about the statement pages used: [(check, page, detail)]."""
    pg, out = B.get('pages') or {}, []
    own = own_name(pm)
    nm = lambda x: int(re.match(r'\d+', x).group()) if x and re.match(r'\d+', x) else None
    for st in ('bs', 'pl', 'cf'):
        p = pg.get(st)
        if not p or p not in pm:
            continue
        e = A.entity(pm[p])
        rt = A.name_ratio(e, cname)
        if rt is not None and rt < 0.85 and not (own and A.name_ratio(e, [own]) >= 0.85):
            out.append(('entity', p, f'{st} page {p} headed "{e}", not {cname[:2]}'))
        if st != 'cf' and not A.stmt_head(pm[p], st):
            head = ' '.join(pm[p][:2500].split()).upper()
            if not re.search(A.HEAD_LOOSE[st], head[:900]) or re.search(r'SCHEDULES?\s*TO|SCHEDULES?\s*FORMING', head[:200]):
                out.append(('page_head', p, f'{st} page {p} is not headed as the statement: "{" ".join(pm[p].split())[:60]}"'))
    a_, c_ = nm(pg.get('bs')), nm(pg.get('pl'))
    if a_ is not None and c_ is not None:
        if abs(a_ - c_) > 12:
            out.append(('page_far', pg.get('pl'), f'balance sheet p{a_} and P&L p{c_} are far apart'))
        cons = lambda t: 'CONSOLIDATED' in ' '.join(t[:2500].split()).upper()[:600]
        heads = {st: [nm(p) for p, t in pm.items() if nm(p) is not None and A.stmt_head(t, st) and cons(t) == (b == 'consolidated')]
                 for st in ('bs', 'pl')}
        ear = [x for x in heads['bs'] if x < min(a_, c_) and any(0 < abs(y - x) <= 3 for y in heads['pl'])]
        if ear:
            out.append(('page_earlier', pg.get('bs'), f'earlier adjacent statement pages at p{ear[0]}; read from p{a_}/p{c_}'))
    for st in ('bs', 'pl'):
        if pg.get(st) in pm:
            tk = [t[0] for l in pm[pg[st]].splitlines() for t in A.tokens(l)]
            com = [t for t in tk if ',' in t]
            if len(com) >= 5 and sum(1 for t in com if re.search(r',\d\d\)?$', t)) >= 0.5 * len(com):
                out.append(('comma_decimal', pg[st], f'{st} page {pg[st]}: figures like {com[0]} have a comma for the decimal point; printed unit "{(B.get("unit") or {}).get(st)}"'))
                break
    if B.get('unit_missing'):
        out.append(('unit_missing', '', 'no unit on the statements'))
    u = B.get('unit') or {}
    ua, ub = A.unit_of(u.get('bs') or '')[0], A.unit_of(u.get('pl') or '')[0]
    if ua and ub and ua != ub:
        out.append(('unit_mismatch', '', f'balance sheet in "{u.get("bs")}", P&L in "{u.get("pl")}"'))
    return out


def check_cf(F, y, k, keys, r, text):
    ix = 0 if k == r.get('year_end') else 1 if len(keys) > 1 and k == keys[1] else None
    if ix is None:
        return
    c = cf_lines(text)
    if 'cfo' not in c or not c['cfo'][1][ix]:
        return
    lab, pair = c['cfo']
    v = y['cfo'][0]
    if not v or pw(abs(v) / abs(pair[ix]), 0.05) is None:
        return  # another figure than the page's line
    exp = A.cfo_signed(lab, pair)[ix]
    if exp * v < 0:
        F('cfo', 'cfo_sign', f'printed "{lab[:50]}" {pair[ix]:g} means {"outflow" if exp < 0 else "inflow"}, value {v:g}')
    elif all(x in c and c[x][1][ix] is not None for x in ('cfi', 'cff', 'net')):
        sc = abs(v) / abs(pair[ix])
        cfi, cff = A.cfo_signed(*c['cfi'])[ix] * sc, A.cfo_signed(*c['cff'])[ix] * sc
        net = c['net'][1][ix] * sc
        tol = max(0.02, 0.005 * max(abs(v), abs(cfi), abs(cff)))
        ok = lambda s: abs(s * v + cfi + cff - net) <= tol or abs(s * v + cfi + cff + net) <= tol
        if not ok(1) and ok(-1):
            F('cfo', 'cfo_sign', f'operating {v:g} + investing {cfi:g} + financing {cff:g} matches net {net:g} only with the opposite sign')


def check_report(sym, jf, r, hp, raw, flag, ctx):
    rep = os.path.basename(jf)[3:-5]
    V = values(r, hp, raw)
    cache = {}

    def page_map():
        if 'pm' not in cache:
            pf = r.get('pages_real') or jf[:-5] + '_pages.txt'
            cache['pm'] = {k: t.translate(A.LIG) for k, t in A.respread(A.read_pages_file(pf))} if os.path.exists(pf) else {}
        return cache['pm']
    cname = ctx.names(sym)
    for b, Y in V.items():
        B = (r.get('bases') or {}).get(b) or {}
        bank = bool(B.get('bank'))
        keys = sorted(Y, reverse=True)
        pg = B.get('pages') or {}
        parsed = {k: any(v[1] != 'helper' for v in Y[k].values()) for k in Y}
        notes = page_notes(sym, B, b, page_map(), cname) if pg and any(parsed.values()) else []
        ubs = A.unit_of((B.get('unit') or {}).get('bs') or '')[0]
        for j, k in enumerate(keys):
            y = Y[k]
            g = lambda f: y[f][0] if f in y else None
            F = lambda field, check, detail: flag(sym, rep, b, k, field, g(field), check, detail, rep)
            if parsed.get(k):
                for chk, p, det in notes:
                    flag(sym, rep, b, k, 'statement_page', p, chk, det, rep)
            pbt, tax, pat = g('pbt'), g('tax'), g('pat')
            if None not in (pbt, tax, pat):
                tol = max(0.05, 0.015 * max(abs(pat), abs(pbt)))
                if abs(pbt - abs(tax) - pat) > tol and abs(pbt - tax - pat) > tol:
                    F('pat', 'pbt_tax_pat', f'pbt {pbt:g} - tax {tax:g} = {pbt - tax:g}, pat {pat:g}')
            eq, res, bor, ta = g('equity_cap'), g('reserves'), g('borrowings'), g('total_assets')
            if None not in (eq, res, ta) and ta > 0:
                s = eq + res + (bor or 0)
                if s > ta * 1.01:
                    F('total_assets', 'bs_identity', f'equity {eq:g} + reserves {res:g} + borrowings {bor or 0:g} = {s:g} above total assets {ta:g}')
                elif bor is not None and not bank and s < 0.1 * ta and res > 0:
                    F('total_assets', 'bs_identity', f'equity + reserves + borrowings {s:g} under 10% of total assets {ta:g}')
            if ta == 0:
                F('total_assets', 'internal_scale', 'total assets of zero')
            base = max(abs(g('sales') or 0), abs(ta or 0))
            for f in ('pbt', 'pat', 'equity_cap', 'reserves', 'borrowings', 'cfo'):
                if g(f) and base and abs(g(f)) > 5 * base:
                    F(f, 'internal_scale', f'{f} {g(f):g} over 5x the larger of sales and total assets ({base:g})')
            sa = g('sales')
            if sa and ta and sa > 0 and ta > 0 and not bank and (sa / ta > 300 or ta / sa > 300):
                F('sales', 'internal_scale', f'sales {sa:g} and total assets {ta:g} are 300x apart')
            if 'cfo' in y and pg.get('cf') and page_map().get(pg['cf']):
                check_cf(F, y, k, keys, r, page_map()[pg['cf']])
            if eq and y['equity_cap'][1] != 'helper' and pg.get('bs') and ubs:
                ep = A.pref_split(page_map(), pg['bs'], eq, ubs)
                if ep:
                    F('equity_cap', 'equity_pref', f'schedule: equity {ep[0]:g} + preference {ep[1]:g} = {eq:g}')
            for y2, rep2 in ctx.same(sym, b, k, jf):
                for f in CROSS:
                    a, c = g(f), y2.get(f)
                    if not a or not c or (abs(a) < 0.5 and abs(c) < 0.5):
                        continue
                    if a * c < 0:
                        if abs(abs(a) - abs(c)) <= 0.02 * abs(a):
                            F(f, 'cross_sign', f'{a:g} here, {c:g} in report {rep2}')
                        continue
                    n = pw(abs(a / c), 0.15)
                    if n:
                        F(f, 'cross_scale', f'{a:g} here, {c:g} in report {rep2} (10^{n})')
                    elif n is None and not 0.67 <= abs(a / c) <= 1.5:
                        F(f, 'cross_value', f'{a:g} here, {c:g} in report {rep2}')
            for nk, y2, rep2 in ctx.near(sym, b, k):
                offs = {}
                for f in ('sales', 'total_assets', 'reserves', 'equity_cap', 'pat'):
                    a, c = y2.get(f), g(f)
                    if a and c and a > 0 and c > 0:
                        n = pw(a / c, 0.6)
                        if n and abs(n) >= 2:
                            offs[f] = n
                if len(offs) >= 2 and len(set(offs.values())) == 1:
                    F('sales' if 'sales' in offs else next(iter(offs)), 'year_scale', f'{sorted(offs)} jump 10^{next(iter(offs.values()))} to {nk} in report {rep2}')
            for st, fs in SCR.items():
                T = ctx.scr(sym, st, b).get(k)
                if not T:
                    continue
                for f, labs in fs.items():
                    a, c = g(f), next((num(T.get(x)) for x in labs if num(T.get(x)) is not None), None)
                    if not a or not c or (abs(a) < 0.5 and abs(c) < 0.5):
                        continue
                    if a * c < 0:
                        if abs(abs(a) - abs(c)) <= 0.1 * abs(a):
                            F(f, 'scr_sign', f'{a:g} here, screener {c:g}')
                        continue
                    n = pw(abs(a / c), 0.15)
                    if n:
                        F(f, 'scr_scale', f'{a:g} here, screener {c:g} (10^{n})')
                    elif n is None and not 0.67 <= abs(a / c) <= 1.5:
                        F(f, 'scr_value', f'{a:g} here, screener {c:g}')
            cv = ctx.chart(sym, k)
            if cv and sa and sa > 0:
                others = [Y2[k]['sales'][0] for Y2 in V.values() if k in Y2 and Y2[k].get('sales') and Y2[k]['sales'][0]]
                if not any(0.5 <= abs(x) / cv <= 2 for x in others):
                    F('sales', 'chart_scale' if pw(sa / cv, 0.15) else 'chart_value', f'sales {sa:g}, chart TTM {cv:g} (x{sa / cv:.3g})')
        used = [page_map()[p] for p in pg.values() if p in page_map()]
        ye = A.report_year(used)[0] if used else None
        if keys and ye and r.get('year_end') and ye.isoformat()[:7] != r['year_end']:
            flag(sym, rep, b, keys[0], 'year', keys[0], 'year_end', f'labelled {r["year_end"]}; the statement pages say {ye.isoformat()[:7]}', rep)
        months = r.get('months') or 12
        if keys and months != 12:
            if len(keys) > 1:
                true = A.prev_year_key(keys[0], months)
                if keys[1] != true:
                    flag(sym, rep, b, keys[1], 'year', keys[1], 'year_label', f'previous column labelled {keys[1]}; {months} months before {keys[0]} is {true}', rep)


class Ctx:
    def __init__(self, reports, raw):
        import mb_features as mf
        self.mf = mf
        self.vals = collections.defaultdict(list)  # (sym, basis, key) -> [(jf, {field: value}, report)]
        for sym, jf, r, hp in reports:
            for b, Y in values(r, hp, raw).items():
                for k, y in Y.items():
                    self.vals[(sym, b, k)].append((jf, {f: v[0] for f, v in y.items()}, os.path.basename(jf)[3:-5]))
        self._nm, self._scr, self._ch = {}, {}, {}

    def names(self, sym):
        if sym not in self._nm:
            self._nm[sym] = A.company_names(sym)
        return self._nm[sym]

    def near(self, sym, b, k):
        """The same basis's values for the years just before and after k, from any report."""
        out = []
        for d in (-1, 1):
            nk = f'{int(k[:4]) + d}{k[4:]}'
            out += [(nk, y, rep) for _, y, rep in self.vals.get((sym, b, nk), [])]
        return out

    def same(self, sym, b, k, jf):
        return [(y, rep) for j2, y, rep in self.vals.get((sym, b, k), []) if j2 != jf]

    def scr(self, sym, st, b):
        if (sym, st, b) not in self._scr:
            self._scr[(sym, st, b)] = scr_table(sym, st, b)
        return self._scr[(sym, st, b)]

    def chart(self, sym, k):
        if sym not in self._ch:
            self._ch.clear()
            try:
                self._ch[sym] = self.mf.Company(sym, A.COMP, chart_only=True)
            except Exception:
                self._ch[sym] = None
        c = self._ch[sym]
        if not c or not c.sales.raw:
            return None
        return c.sales.lookup(self.mf.month_end(int(k[:4]), int(k[5:])) + dt.timedelta(days=75)) or None


def run(D, syms, raw, comp=None):
    reports = []
    for sym, jf in report_list(D, syms, comp):
        r = A.load(jf) or {}
        hp = A.load(jf[:-5] + '_helper.json') or {}
        if raw:
            reports.append((sym, jf, r, {}))
        elif not hp.get('wrong_report'):
            reports.append((sym, jf, r, hp))
    ctx = Ctx(reports, raw)
    rows, seen, used_cache = [], set(), {}

    def used(sym, b, k, rep):
        if sym not in used_cache:
            used_cache[sym] = A.load_ar(sym, comp or A.COMP)
        y = used_cache[sym].get(b, {}).get(k)
        has = lambda st: any(num(v) is not None for v in (ctx.scr(sym, st, b).get(k) or {}).values())
        return bool(y) and y['report'] == rep and not has('profit_loss') and not has('balance_sheet')

    def flag(sym, fy, b, k, field, value, check, detail, rep):
        key = (sym, fy, b, k, field, check, detail)
        if key not in seen:
            seen.add(key)
            u = used(sym, b, k, rep) and (field in FEATURE_FIELDS or field in ('statement_page', 'year'))
            rows.append({'sym': sym, 'fy': fy, 'basis': b, 'year': k, 'field': field, 'value': '' if value is None else value,
                         'check': check, 'detail': ('[used] ' if u else '[unused] ') + detail})
    errs = []
    for sym, jf, r, hp in sorted(reports, key=lambda x: x[0]):
        try:
            check_report(sym, jf, r, hp, raw, flag, ctx)
        except Exception as e:
            errs.append((sym, jf, repr(e)))
    return rows, errs, reports


# the faults annual-report subagents found (Nov 2026 parser check): (sym, report, basis, year, field, checks that count as caught, what it is)
PG = ('page_far', 'page_head', 'page_earlier', 'entity')
KNOWN = [('GESHIP', f'FY{y:02d}', None, None, None, PG, 'subsidiary pages') for y in (4, 6, 8, 10)] + \
    [('GOLDIAM', 'FY05', None, None, None, PG, 'subsidiary pages'), ('GOLDIAM', 'FY07', None, None, None, PG, 'subsidiary pages'),
     ('HEXT', 'FY10', None, None, None, PG, 'subsidiary pages'), ('IDFC', 'FY04', None, None, None, PG, 'subsidiary pages'),
     ('IDFC', 'FY08', None, None, None, PG, 'subsidiary pages'), ('IDEA', 'FY08', 'standalone', None, None, PG, 'subsidiary pages'),
     ('DLF', 'FY08', 'standalone', '2008-03', 'cfo', ('cfo_sign',), 'cfo sign'), ('IDFC', 'FY12', 'consolidated', '2012-03', 'cfo', ('cfo_sign',), 'cfo sign'),
     ('IL&FSENGG', 'FY10', 'consolidated', '2010-03', 'cfo', ('cfo_sign',), 'cfo sign'),
     ('ICICIBANK', 'FY06', 'consolidated', None, None, ('year_scale', 'cross_scale', 'chart_scale'), 'scale'),
     ('GOLDIAM', 'FY07', None, None, None, ('unit_missing', 'internal_scale'), 'scale'),
     ('GAIL', 'FY03', None, None, None, ('comma_decimal',), 'scale'),
     ('3IINFOLTD', 'FY11', 'consolidated', '2011-03', 'equity_cap', ('equity_pref',), 'preference capital'),
     ('M&MFIN', 'FY06', None, None, 'equity_cap', ('equity_pref',), 'preference capital'),
     ('JINDALSAW', 'FY06', None, None, 'year', ('year_end',), 'year end'),
     ('HINDUNILVR', 'FY09', None, '2008-03', 'year', ('year_label',), 'long year'), ('IL&FSENGG', 'FY12', None, '2011-09', 'year', ('year_label',), 'long year'),
     ('GMRAIRPORT', 'FY08', 'consolidated', '2008-03', 'pat', ('pbt_tax_pat', 'cross_value'), 'pat = pbt'),
     ('GMDCLTD', 'FY12', 'standalone', '2012-03', None, ('bs_identity', 'cross_value'), 'reserves')]
CLOSE = lambda x, y: abs(x - y) <= max(0.02, 0.015 * max(abs(x), abs(y)))


def clean_years(reports):
    """(sym, report, basis, year) -> True when a subagent read fields of that parsed year and all agreed, False when any didn't."""
    out = {}
    for sym, jf, r, _ in reports:
        hp = A.load(jf[:-5] + '_helper.json') or {}
        rep = os.path.basename(jf)[3:-5]
        for b, ys in (hp.get('bases') or {}).items():
            for k, h in ys.items():
                py = (((r.get('bases') or {}).get(b) or {}).get('years') or {}).get(k, {}).get('fields') or {}
                pairs = [(py[f][0], v) for f, v in h.items() if f in A.FIELDS and isinstance(v, (int, float)) and f in py]
                if pairs:
                    ok = all(CLOSE(a, c) for a, c in pairs)
                    if pairs:
                        out[(sym, rep, b, k)] = ok
    return out


def clean_by_screener(reports, ctx):
    """Parsed years that overlap screener's saved statements: (sym, report, basis, year) of those where 3+ fields agree within 5%."""
    out = set()
    for sym, jf, r, _ in reports:
        rep = os.path.basename(jf)[3:-5]
        for b, Y in values(r, {}, True).items():
            for k, y in Y.items():
                agree = []
                for st, fs in SCR.items():
                    T = ctx.scr(sym, st, b).get(k) or {}
                    for f, labs in fs.items():
                        c = next((num(T.get(x)) for x in labs if num(T.get(x)) is not None), None)
                        if f in y and c:
                            agree.append(abs(y[f][0] - c) <= 0.05 * abs(c))
                if len(agree) >= 3 and all(agree):
                    out.add((sym, rep, b, k))
    return out


def test(D, comp=None):
    for raw in (True, False):
        rows, errs, _ = run(D, {k[0] for k in KNOWN}, raw, comp)
        print('--', 'parsed values' if raw else 'final values', len(rows), 'flags; errors', errs[:3])
        for s_, rp, b, y, f, chk, what in KNOWN:
            hit = [x for x in rows if x['sym'] == s_ and x['fy'] == rp and (not b or x['basis'] == b) and (not y or x['year'] == y) and
                   (not f or x['field'] == f) and x['check'] in chk]
            print(f'  {s_} {rp} {b or ""} {y or ""} {f or ""} [{what}]:', 'caught ' + ','.join(sorted({x['check'] for x in hit})) if hit else 'MISSED')
    rows, errs, reports = run(D, None, True, comp)
    cy = clean_years(reports)
    n = collections.Counter(cy.values())
    print(f'years a subagent read: clean {n[True]}, parser wrong {n[False]}; per check: years flagged (clean / wrong)')
    fired = collections.defaultdict(lambda: {True: set(), False: set()})
    for x in rows:
        st = cy.get((x['sym'], x['fy'], x['basis'], x['year']))
        if st is not None:
            fired[x['check']][st].add((x['sym'], x['fy'], x['basis'], x['year']))
    for c, d in sorted(fired.items()):
        print(f'  {c}: {len(d[True])} ({len(d[True]) / max(1, n[True]):.1%}) / {len(d[False])} ({len(d[False]) / max(1, n[False]):.1%})')
    cs = clean_by_screener(reports, Ctx(reports, True))
    c = collections.Counter(x['check'] for x in {(x['sym'], x['fy'], x['basis'], x['year'], x['check']): x for x in rows}.values()
                            if (x['sym'], x['fy'], x['basis'], x['year']) in cs and not x['check'].startswith('scr_'))
    print(f'years screener confirms: {len(cs)}; years flagged per check:', {k: f'{v} ({v / max(1, len(cs)):.1%})' for k, v in c.most_common()})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--syms', help='comma-separated symbols, e.g. A,B (limit)')
    p.add_argument('--raw', action='store_true', help="the parser's own values (see above)")
    p.add_argument('--out', help='flags file (default: ar_parsed_flags.csv in the playbook base data folder)')
    p.add_argument('--test', action='store_true', help='the known faults, caught or missed; writes nothing')
    p.add_argument('--comp', metavar='DIR', help='reports from another tree (see above)')
    a = p.parse_args()
    D = playbook_dir()
    if a.test:
        return test(D, a.comp)
    rows, errs, reports = run(D, set(a.syms.split(',')) if a.syms else None, a.raw, a.comp)
    out = a.out or os.path.join(D, 'ar_parsed_flags.csv')
    with open(out + '.tmp', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    os.replace(out + '.tmp', out)
    print(len(reports), 'reports,', len(rows), 'flags ->', out, '; errors', len(errs), errs[:3])
    for lab, sel in (('all', rows), ('feature fields', [x for x in rows if x['detail'].startswith('[used]')])):
        print(lab, len(sel), 'reports', len({(x['sym'], x['fy']) for x in sel}), dict(collections.Counter(x['check'] for x in sel).most_common()))


if __name__ == '__main__':
    main()
