import argparse, collections, csv, datetime as dt, glob, json, os, re, shutil, subprocess, sys, tempfile, time, zipfile
# Multibagger study (process/historical/s3_statements.md, s4_backtest.md): annual statements for the years before screener's
# statements (screener has ~12 years), read from the annual reports. Plain curl with its default identity; no model tokens.
#   python -I tools/scripts/ar_statements.py plan  [--rows FILE] [--groups winner,fallen_winner]   -> <run>/ar_plan.csv
#   python -I tools/scripts/ar_statements.py fetch [--gap 1.5] [--syms A,B] [--tmp DIR]   download, extract, parse (resumable)
#   python -I tools/scripts/ar_statements.py reparse [--syms A,B]   re-parse the saved page text (after a parser fix)
#   python -I tools/scripts/ar_statements.py queue [--per 25]   -> <run>/ar_missing.csv, ar_helper_queue.csv, ar_summary.md
#   python -I tools/scripts/ar_statements.py parse REPORT.pdf|PAGES.txt [--fy 2008]   one report, printed (debugging)
# plan: for each (sym, as_of) row, the fiscal years the features need (mb_features.py: the latest FY filed by as_of and 4
#   before it, plus one more when the newest cash flow isn't filed yet), minus the years screener's statements have and the
#   years before listing. Reports: newest needed year first; each report also gives the year before (its previous-year
#   column), so report y covers y and y-1.
# fetch, per needed report year ry (newest first; when report ry isn't found, report ry+1 is tried for its previous-year
#   column): candidate links in order (0) <run>/ar_links.csv (sym, fy, url: links the orchestrator found in BSE's
#   annual-report list in the browser pane for ar_missing.csv rows; a not-found report is retried), (1) screener's annual-report list (scr/documents.json, back to ~FY13), (2) BSE
#   bseplus/AnnualReport/<code>/<code><MM><yy>.pdf (FY10 on), (3) BSE HIS_ANN_RPT/HISTANNR/<y>/<NAME>-<code>-MARCH-<y>.PDF,
#   y = the year the fiscal year ends (MARCH even for other year-ends), NAME = the company's BSE name of the time, guessed
#   from today's screener and BSE names (a renamed company misses). BSE code: bse_shp.bse_code (screener, then
#   data/market/bse_codes.csv). A downloaded PDF is converted with xpdf `pdftotext -table -enc UTF-8`; the statement pages
#   (balance sheet, P&L, cash flow, both bases, with the page after each) are saved and the PDF deleted (URL recorded).
#   The report's year is read from its statement headings, not assumed from the link.
# Saved per report, in data/companies/<SYM>/FY<yy>Q4/ (yy = the year its fiscal year ends):
#   ar_FY<yy>_pages.txt  the statement pages, '=== page N ===' markers (N = page in the PDF)
#   ar_FY<yy>.json       url, pages, unit, per basis per year (year-end date): fields in Rs crore (EPS in Rs) with per-field
#                        confidence and source page, checks, notes, and 'helper' = fields a helper must read
#   ar_FY<yy>_helper.json  written by a fallback helper (process/historical/s4_ar_helper_brief.md); overrides parsed fields
# Fields (screener's definitions): sales (net of excise; banks: interest earned), other_income (incl. exceptional items),
#   interest, dep, pbt, tax, pat (before minority interest), eps (basic, as reported), dividend (proposed/paid on equity,
#   excl. tax), op (= pbt + interest + dep - other_income), equity_cap, reserves (incl. share warrants), borrowings (all
#   loans; banks: deposits too), total_assets (old Schedule VI: funds employed + current liabilities and provisions),
#   debtors, cfo. Helpers get a field when it is missing, when two values land on one year's side, or a check fails.
# Status: <run>/ar_status.csv, one row per report tried (parsed / needs-helper / not-found / scanned / error).
# Other income and operating profit are classified differently from screener's old data: mb_features.py keeps report and
# screener years apart in margin trends.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import hist_dir

COMP = os.path.join('data', 'companies')
KEEP_PDF = None  # --keep-pdf DIR: keep a copy of each PDF (debugging)
MON = {m: i for i, m in enumerate(['', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])}
FIELDS = ['sales', 'other_income', 'interest', 'dep', 'pbt', 'tax', 'pat', 'eps', 'dividend', 'op', 'equity_cap', 'reserves',
          'borrowings', 'total_assets', 'debtors', 'cfo']
NEED = ['sales', 'other_income', 'interest', 'dep', 'pbt', 'tax', 'pat', 'eps', 'dividend', 'equity_cap', 'reserves',
        'borrowings', 'total_assets', 'debtors', 'cfo']
NEED_BANK = ['sales', 'interest', 'pbt', 'tax', 'pat', 'eps', 'dividend', 'equity_cap', 'reserves', 'borrowings',
             'total_assets', 'cfo']
STATUS_COLS = ['sym', 'report_fy', 'fym', 'code', 'src', 'url', 'result', 'years', 'bases', 'helper_fields', 'pages_file',
               'json_file', 'mb', 'note', 'at']

# ------------------------------------------------------------------ parser ------------------------------------------------
UNIT = [(r'crores?|cr\.', 1.0), (r'lakhs?|lacs?', 0.01), (r'millions?|mn\b', 0.1), (r"thousands?|['’]000", 1e-4)]
NUM = re.compile(r'(\(-\)\s*|-\s?)?\(?\d[\d,]*(\.\d+)?\)?(?=\s|$)|(?<=\s)[—–-](?=\s|$)')
HEAD = {'bs': r'BALANCE\s*SHEET\s*AS\s*(A[TS]|ON)',
        'pl': r'PROFIT\s*(AND|&)\s*LOSS\s*(ACCOUNT|STATEMENT)?\s*FOR|STATEMENT\s*OF\s*PROFIT\s*(AND|&)\s*LOSS|'
              r'PROFIT\s*(AND|&)\s*LOSS\s*ACCOUNT',
        'cf': r'CASH\s*-?\s*FLOW\s*STATEMENT|STATEMENT\s*OF\s*CASH\s*-?\s*FLOWS?'}
F = {  # field: label regexes (lower-case label, schedule refs removed); first matching line wins unless noted
    'bs': [('share_capital', r'^(equity )?share capital|^capital$'),
           ('warrants', r'share warrants|money received against share warrants'),
           ('reserves', r'^reserves? (and|&) surplus|^other equity'),
           ('minority', r'^minority interest'),
           ('dtl', r'^deferred tax liabilit(y|ies)( \(net\))?$'),
           ('secured', r'^secured loans'), ('unsecured', r'^unsecured loans'),
           ('lt_borr', r'^long[- ]term borrowings'), ('st_borr', r'^short[- ]term borrowings'),
           ('borr', r'^borrowings'), ('deposits', r'^deposits\b'),
           ('debtors', r'^sundry debtors|^trade receivables'),
           ('cl', r'^current liabilities$|^liabilities$'), ('prov', r'^provisions$'),
           ('total', r'^total\b|total funds employed|^total (equity and liabilities|assets)')],
    'pl': [('net_ops', r'^net income from operations|^revenue from operations \(net\)|^total revenue from operations'),
           ('net_sales', r'^net (sales|income from operations|revenue from operations|turnover)|^revenue from operations \(net\)|^sales \(net\)'),
           ('gross_sales', r'^(gross )?(sales|income from operations|revenue from operations|turnover)\b'),
           ('excise', r'excise duty'),
           ('int_earned', r'interest ear[nh]ed'), ('int_expended', r'interest expended'),
           ('other_income', r'^other income'), ('int_income', r'^(add:? )?interest income'),
           ('total_income', r'^total (income|revenue)$'),
           ('pat_pre_mi', r'before minority interest|before share of (profit|loss)'),
           ('interest', r'^(less:? )?(interest|finance (costs?|charges|expenses))(?!.*(income|received|earned))'),
           ('dep', r'^(less:? )?depreciation'),
           ('exceptional', r'^exceptional items?\b'),
           ('pbt', r'profit.*before (tax|taxes|taxation)$|profit.*before (tax|taxes|taxation)\b(?!.*exceptional)|before tax(es|ation)?$|'
                   r'^profit after exceptional items$'),
           ('tax_total', r'^total tax(ation)?( expenses?)?$|^tax expenses?$|^total (provision for )?tax|^total income tax'),
           ('tax', r'^(provision for )?(tax|taxes|taxation|income tax)(?!.*dividend)'),
           ('pat', r'^net profit|profit (for the year|after tax(ation)?)\b|loss after tax|profit/?\s*\(?(-\)\s*)?loss\)? (for the year|after tax)'),
           ('eps', r'^(basic.*)?earnings? per (equity )?share|^basic\b|^eps\b'),
           ('div_interim', r'^interim dividend(?!.*(tax|preference))'),
           ('div_final', r'^(proposed|final)( final)? dividend(?!.*(tax|preference))|^proposed dividend on equity'),
           ('div_plain', r'^dividends?\b(?!.*(tax|preference))'),
           ('approp', r'balance (carried|transferred) to (the )?balance sheet|^balance carried forward|^surplus carried')],
    'cf': [('cfo', r'net cash.*operating activit|cash (generated )?(flow )?from operating activities.*\(a\)|net cash.*\(a\)$')],
}


def pdf_pages(pdf):
    """[(page id, text)]: one per PDF page; a two-up spread (two statements side by side) becomes '<n>L' and '<n>R'."""
    out = subprocess.run(['pdftotext', '-q', '-enc', 'UTF-8', '-table', pdf, '-'], capture_output=True, timeout=600)
    res = []
    for i, t in enumerate(out.stdout.decode('utf-8', 'replace').split('\f')):
        parts = split_spread(t)
        res += [(str(i + 1), t)] if len(parts) == 1 else [(f'{i + 1}L', parts[0]), (f'{i + 1}R', parts[1])]
    return res


def split_spread(t):
    """Cut a page vertically where a second statement heading starts (x > 60) on one of its first lines, when there is
    text to its left (a two-up spread)."""
    lines = t.splitlines()
    for l in lines[:12]:
        u = l.upper()
        for s in HEAD:
            for m in re.finditer(HEAD[s], u):
                x = m.start()
                if x <= 60 or not re.search(r'[A-Za-z]{3}', l[:x]):
                    continue
                best = x  # back up to a column that is blank in nearly all lines
                for c in range(x, max(40, x - 30), -1):
                    if sum(1 for z in lines if len(z) > c and z[c] != ' ') <= max(1, len(lines) * 0.03):
                        best = c
                        break
                left = '\n'.join(z[:best] for z in lines)
                right = '\n'.join(z[best:] for z in lines)
                if len(re.sub(r'\s', '', left)) > 200 and len(re.sub(r'\s', '', right)) > 200:
                    return [left, right]
    return [t]


def stmt_head(text, stmt):
    """True when the page opens with the statement's own heading (not a schedule, note or report that names it)."""
    head = ' '.join(text[:2500].split()).upper()
    m = re.search(HEAD[stmt], head)
    if not m or m.start() > 900:
        return False
    return not re.search(r'SCHEDULES?\s|NOTES?\s(TO|FORMING|ON)|FORMING\s*PART|ANNEXED|REFERRED|AUDITOR|ADOPT|CONSIDER',
                         head[max(0, m.start() - 80):m.start()])


def val(tok):
    t = tok.strip()
    if t in '—–-':
        return 0.0
    neg = t.startswith('(') or t.startswith('-')
    v = float(re.sub(r'[^\d.]', '', t) or 'nan')
    return -v if neg else v


def tokens(line):
    return [(m.group(0), m.start(), m.end()) for m in NUM.finditer(line)]


def unit_of(text):
    t = text.lower()
    us = '|'.join(u for u, _ in UNIT)
    m = re.search(r'(rs\.?|₹|rupees|inr|`)\s*(in\s*)?(' + us + ')', t) or \
        re.search(r'\(\s*(in\s*)?(' + us + r')\s*\)', t) or re.search(r'\(\s*rs[^)]{0,8}(' + us + r')\s*\)', t) or \
        re.search(r'\b(figures|amounts?)\s*(are\s*)?in\s*(' + us + r')', t)
    if not m and re.search(r'\bin\s*(rs\.?|₹|`|rupees|inr)(?!\s*\.?\s*(in\s*)?(' + us + r'|\d))|'
                           r'\(\s*(in\s*)?(rs\.?|₹|`|rupees|inr)\s*\)', t, re.M):
        return 1e-7, 'rupees'  # '(Amount in `)': whole rupees, even if 'lakh' appears elsewhere on the page
    m = m or re.search(r'\b(' + us + r')', t)
    if m:
        for u, f in UNIT:
            if re.search(u, m.group(0)):
                return f, m.group(0)
    if re.search(r'\brupees\b|\bamount in rs\b|\(rs\.?\)|\brs\.?\s*$', t, re.M):
        return 1e-7, 'rupees'
    return None, ''


def columns(lines):
    """Value columns: right edges of comma/decimal numbers that recur on the page."""
    ends = sorted(e for l in lines for t, s, e in tokens(l) if (',' in t or '.' in t) and len(re.sub(r'\D', '', t)) >= 3)
    cl = []
    for e in ends:
        if cl and e - cl[-1][-1] <= 4:
            cl[-1].append(e)
        else:
            cl.append([e])
    return [max(c) for c in cl if len(c) >= 3]


def split_at(lines, cols):
    """The x that separates the current year from the previous one: with an even number of value columns (one or two
    per year), the middle; otherwise the column gap nearest the middle of the two header years (or Current/Previous)."""
    cols = sorted(cols)
    gaps = [(a + b) / 2 for a, b in zip(cols, cols[1:])]
    if not gaps:
        return None
    if len(cols) % 2 == 0:
        return gaps[len(gaps) // 2]
    for l in lines[:25]:
        ys = [m.end() for m in re.finditer(r'(19|20)\d\d\b', l)]
        cp = re.search(r'current\s+year', l, re.I), re.search(r'previous\s+year', l, re.I)
        h = ys[:2] if len(ys) == 2 and ys[1] - ys[0] > 8 else [cp[0].end(), cp[1].end()] if all(cp) else None
        if h:
            return min(gaps, key=lambda g: abs(g - sum(h) / 2))
    return None


def clean_label(label):
    label = re.sub(r'\s+', ' ', label).strip().lower()
    if '/' in label:
        a_, b_ = label.rsplit('/', 1)
        if (re.search(r'[^\x20-\x7e]|[\^<>{}~|*?]', a_) or label.count(' / ') == 1 and 'profit' not in a_) and \
                re.search(r'[a-z]{4}', b_) and not re.match(r'\s*\(?\s*(loss|-)', b_):
            label = b_.strip()  # bilingual 'Hindi / English' labels keep the English part
    label = re.sub(r"[^a-z0-9()&/,.:'\- ]", '', label).strip()
    label = re.sub(r'\(\s*loss\s*\)\s*/\s*|/\s*\(?\s*(\(-\)\s*)?loss\s*\)?|\(-\)\s*', ' ', label)
    label = re.sub(r'\s+', ' ', label).strip()
    label = re.sub(r'^([ivx]+\.|\(?[a-z0-9]{1,3}\)|[a-z]\.|\d+\.)\s*', '', label)
    label = re.sub(r'^([ivx]{1,4}|\d{1,2})\s+(?=[a-z(])', '', label)  # 'ii other income', '3 other income'
    label = re.sub(r'^\(?[a-z0-9]{1,3}\)\s*', '', label)
    return re.sub(r'\s+(\d{1,2}(\.\d+)?|[a-z]|\d+\s?[a-z])$', '', label).strip(' :.-')  # schedule / note refs


def parse_page(text, stmt):
    """{field: [current, previous]} in the page's own unit, notes, the year split x, and {field: 'several'} flags."""
    lines = text.splitlines()
    cols = columns(lines)
    mid = split_at(lines, cols)
    out, notes, pending, flags, unl = {}, [], '', {}, []
    after_less = False
    for l in lines:
        strong = lambda t: (',' in t[0] or '.' in t[0]) and len(re.sub(r'\D', '', t[0])) >= 3
        tk = [t for t in tokens(l) if any(abs(t[2] - c) <= 4 for c in cols) or
              (cols and (strong(t) and t[2] >= min(cols) - 15 or t[0] in '—–-' and t[2] >= min(cols) - 6))]
        label = clean_label(l[:tk[0][1]] if tk else l)
        if 'current liabilities' in label and ('less' in label or 'provisions' in label):
            after_less = True
        if not tk:
            pending = label if label and len(label) < 90 else ''
            continue
        if not label and not pending:  # unlabeled subtotal: the funds-employed total repeats (sources = application)
            pair = [cur_ for cur_ in ([val(t) for t, s, e in tk if mid is None or e <= mid][-1:] or [None])] +                    ([val(t) for t, s, e in tk if mid is not None and e > mid][-1:] or [None])
            unl.append(tuple(pair))
        if not label and pending:  # value line under its label
            label = pending
        pending = ''
        cur = [val(t) for t, s, e in tk if mid is None or e <= mid]
        prv = [val(t) for t, s, e in tk if mid is not None and e > mid]
        if mid is None and len(cur) == 2:
            cur, prv = cur[:1], cur[1:]
        for fld, rx in F[stmt]:
            if re.search(rx, label):
                if fld in ('cl', 'prov') and not after_less:
                    continue
                pair = [cur[-1] if cur else None, prv[-1] if prv else None]
                if fld == 'cfo' and 'used in' in label and not re.search(r'from|generated|inflow', label):
                    pair = [None if x is None else -x for x in pair]  # 'net cash used in operating activities 1,234'
                if fld == 'borr' and fld in out:
                    out[fld] = [(a or 0) + (b or 0) for a, b in zip(out[fld], pair)]
                    break
                if fld == 'total' and fld in out:
                    out.setdefault('total2', pair)
                    break
                if fld not in out:
                    out[fld] = pair
                    if len(cur) > 1 or len(prv) > 1:
                        notes.append(f'{fld}: several values on one side {cur} {prv}')
                        flags[fld] = 'several'
                break
    if stmt == 'bs' and 'total' not in out:
        rep_ = [p for p, n in collections.Counter(unl).items() if n >= 2 and p[0] is not None]
        if rep_:
            out['total'] = list(max(rep_, key=lambda p: abs(p[0])))
            notes.append('total: repeated unlabeled line (sources = application of funds)')
    return out, notes, mid, flags


def stmt_pages(pgs):
    """{index: [statements]} of pages (pgs = [(id, text)]) that open with a statement heading; when a statement has no
    such page, any page whose head names it (the old, looser test)."""
    hit = {}
    for s in HEAD:
        strict = [i for i, (_, t) in enumerate(pgs) if stmt_head(t, s)]
        loose = strict or [i for i, (_, t) in enumerate(pgs) if re.search(HEAD[s], ' '.join(t[:2500].split()).upper())]
        for i in loose:
            hit.setdefault(i, []).append(s)
    return hit


def find(pgs, stmt):
    """Statement pages by heading, best-scoring page per basis -> {basis: (score, page id, fields, notes, mid, flags)}.
    pgs = [(id, text)]; pages that open with the heading are preferred over pages that merely name it."""
    best = {}
    idx = [i for i, (_, t) in enumerate(pgs) if stmt_head(t, stmt)]
    if not idx:
        idx = [i for i, (_, t) in enumerate(pgs) if re.search(HEAD[stmt], ' '.join(t[:2500].split()).upper())]
    for i in idx:
        pid, p = pgs[i]
        head = ' '.join(p[:2500].split()).upper()
        m = re.search(HEAD[stmt], head)
        basis = 'consolidated' if 'CONSOLIDATED' in head[max(0, m.start() - 200):m.end() + 100] or \
            'CONSOLIDATED' in head[:300] else 'standalone'
        o, n, mid, fl = parse_page(p, stmt)
        if stmt == 'bs' and len(o) < 4 and i + 1 < len(pgs):  # statement split over two pages
            o2, n2, _, fl2 = parse_page(pgs[i + 1][1], stmt)
            o = {**o2, **o}
            fl = {**fl2, **fl}
        if stmt == 'cf' and 'cfo' not in o:
            continue
        score = len(o) + (3 if mid else 0) + (5 if stmt == 'cf' and 'cfo' in o else 0)
        if score > best.get(basis, (0,))[0]:
            best[basis] = (score, pid, o, n, mid, fl)
    return best


def report_year(texts):
    """(year-end date, months) read from the statement headings: the most common 'as at / year ended <date>'."""
    c = collections.Counter()
    months = 12
    for t in texts:
        h = ' '.join(t[:2500].split()).upper()
        for m in re.finditer(r'(AS\s*(AT|ON)|(YEAR|PERIOD)\s*ENDED|ENDED\s*ON|ENDED)\s*(THE\s*)?(\d{1,2})\s*(ST|ND|RD|TH)?\s*'
                             r'(DAY\s*OF\s*)?(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*[,.\s]*((19|20)\d\d)', h):
            c[(int(m.group(9)), MON[m.group(8)])] += 1
        for m in re.finditer(r'(AS\s*(AT|ON)|ENDED(\s*ON)?)\s*(THE\s*)?(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*'
                             r'(\d{1,2})\s*(ST|ND|RD|TH)?\s*[,.]?\s*((19|20)\d\d)', h):  # 'March 31, 2014'
            c[(int(m.group(8)), MON[m.group(5)])] += 1
        for m in re.finditer(r'(AS\s*(AT|ON)|ENDED)\s*(\d{1,2})[./-](\d{1,2})[./-]((19|20)\d\d)', h):
            if 1 <= int(m.group(4)) <= 12:
                c[(int(m.group(5)), int(m.group(4)))] += 1
        m = re.search(r'(FIFTEEN|EIGHTEEN|NINE|SIX|TWELVE|FOURTEEN|SIXTEEN|\d{1,2})\s*MONTHS?\s*(PERIOD\s*)?ENDED', h)
        if m:
            w = {'FIFTEEN': 15, 'EIGHTEEN': 18, 'NINE': 9, 'SIX': 6, 'TWELVE': 12, 'FOURTEEN': 14, 'SIXTEEN': 16}
            months = w.get(m.group(1)) or int(m.group(1)) if m.group(1).isdigit() or m.group(1) in w else 12
    if not c:
        return None, months
    (y, mo), _ = c.most_common(1)[0]
    return dt.date(y, mo, 28), months


def derive(bs, pl, cf, unit, flags, pages):
    """Rs crore figures in screener's terms for current (0) and previous (1) year: {field: [value, confidence, page]}."""
    g = lambda d, k, j: None if d.get(k) is None or d[k][j] is None else d[k][j] * unit
    res = []
    bank = pl.get('int_earned') is not None
    for j in (0, 1):
        r = {}
        conf = lambda st, k: 'low' if flags.get(st, {}).get(k) == 'several' else             ('high' if pages.get(st + '_split') else 'medium')
        put = lambda f, v, st, c=None: r.__setitem__(f, [v, c or conf(st, f), pages.get(st)]) if v is not None else None
        s, sk = g(pl, 'net_ops', j), 'net_ops'
        if s is None:
            s, sk = g(pl, 'net_sales', j), 'net_sales'
        if s is None and g(pl, 'gross_sales', j) is not None:
            s, sk = g(pl, 'gross_sales', j) - (g(pl, 'excise', j) or 0), 'gross_sales'
        put('sales', g(pl, 'int_earned', j) if bank else s, 'pl', conf('pl', 'int_earned' if bank else sk))
        for k in ('interest', 'dep', 'pbt', 'tax', 'pat'):
            put(k, g(pl, k, j), 'pl')
        dv = [g(pl, k, j) for k in ('div_interim', 'div_final')]
        if any(x is not None for x in dv):
            put('dividend', abs(sum(x for x in dv if x is not None)), 'pl')
            if pages.get('div_page'):
                r['dividend'][1:] = ['medium', pages['div_page']]
        elif g(pl, 'div_plain', j) is not None:
            put('dividend', abs(g(pl, 'div_plain', j)), 'pl')
        elif pl.get('approp') is not None:
            put('dividend', 0.0, 'pl', 'arith')  # appropriation section on the page, no dividend line in it
        if bank:
            put('interest', g(pl, 'int_expended', j), 'pl')
        oi = g(pl, 'other_income', j)
        if oi is not None or g(pl, 'int_income', j) is not None:
            oi = (oi or 0) + (g(pl, 'int_income', j) or 0)
        elif not bank and g(pl, 'total_income', j) is not None and s is not None and \
                abs(g(pl, 'total_income', j) - s) <= 0.0005 * max(1, abs(s)):
            put('other_income', 0.0, 'pl', 'arith')  # total income = sales: no other income line
        if oi is not None:
            put('other_income', oi, 'pl')
        if g(pl, 'pat_pre_mi', j) is not None:
            put('pat', g(pl, 'pat_pre_mi', j), 'pl')
        # tax: the total tax line; else PBT - PAT (the lines between them are taxes), confirmed when one tax line equals it
        tt = g(pl, 'tax_total', j)
        if tt is not None:
            put('tax', abs(tt) if 'pbt' in r and 'pat' in r and abs(r['pbt'][0] - abs(tt) - r['pat'][0]) <=
                max(0.005, 0.001 * abs(r['pat'][0])) else tt, 'pl')
        elif 'pbt' in r and 'pat' in r and r['pbt'][1] != 'low' and r['pat'][1] != 'low':
            d_ = r['pbt'][0] - r['pat'][0]
            one = 'tax' in r and abs(abs(r['tax'][0]) - abs(d_)) <= max(0.005, 0.001 * abs(d_))
            put('tax', d_, 'pl', None if one else 'arith')
        elif 'tax' in r:
            r['tax'][1] = 'low'  # one tax line (often current tax only) with nothing to confirm it against
        if pl.get('eps') is not None and pl['eps'][j] is not None:
            put('eps', pl['eps'][j], 'pl')
        ex = g(pl, 'exceptional', j)
        v = lambda k: r[k][0] if k in r else None
        if not bank and None not in (v('pbt'), v('interest'), v('dep'), v('other_income')):
            op = v('pbt') + v('interest') + v('dep') - v('other_income')
            if ex is not None:  # screener counts exceptional items in other income
                r['other_income'][0] += ex
                op -= ex
            cs = [r[k][1] for k in ('pbt', 'interest', 'dep', 'other_income')]
            r['op'] = [op, 'low' if 'low' in cs else 'medium' if 'medium' in cs else 'high', pages.get('pl')]
        put('equity_cap', g(bs, 'share_capital', j), 'bs')
        if g(bs, 'reserves', j) is not None:
            put('reserves', g(bs, 'reserves', j) + (g(bs, 'warrants', j) or 0), 'bs')
        parts = [g(bs, k, j) for k in ('secured', 'unsecured', 'lt_borr', 'st_borr', 'borr') + (('deposits',) if bank else ())]
        if any(p is not None for p in parts):
            put('borrowings', sum(p for p in parts if p is not None), 'bs')
        elif g(bs, 'total', j) is not None and g(bs, 'cl', j) is not None and None not in (v('equity_cap'), v('reserves')):
            # old format, no loan lines: zero only if capital + reserves (+ deferred tax, minority) make up funds employed
            rest = g(bs, 'total', j) - v('equity_cap') - v('reserves') - (g(bs, 'dtl', j) or 0) - (g(bs, 'minority', j) or 0)
            if abs(rest) <= 0.001 * abs(g(bs, 'total', j)):
                put('borrowings', 0.0, 'bs', 'arith')
        if 'borrowings' not in r and g(bs, 'total', j) is not None and pages.get('bs_noloans'):
            put('borrowings', 0.0, 'bs', 'absent')  # no loan or borrowing line anywhere on the balance sheet
        put('debtors', g(bs, 'debtors', j), 'bs')
        t = g(bs, 'total', j)
        if t is not None:
            cl = (g(bs, 'cl', j) or 0) + (g(bs, 'prov', j) or 0)
            put('total_assets', t + cl, 'bs')  # Schedule VI: funds employed + current liabilities; new format: total as is
        put('cfo', g(cf, 'cfo', j), 'cf')
        res.append(r)
    return res, bank


def checks(r):
    """Internal consistency: False = fails (the fields go to a helper)."""
    v = lambda k: r[k][0] if k in r else None
    c = {}
    if None not in (v('pbt'), v('tax'), v('pat')):
        c['pbt-tax=pat'] = abs(v('pbt') - abs(v('tax')) - v('pat')) <= max(0.5, 0.03 * abs(v('pat'))) or \
            abs(v('pbt') - v('tax') - v('pat')) <= max(0.5, 0.03 * abs(v('pat')))
    if v('op') is not None and v('sales'):
        c['opm_plausible'] = -100 < v('op') / v('sales') * 100 < 80
    if v('sales') is not None:
        c['sales_positive'] = v('sales') > 0
    if None not in (v('equity_cap'), v('reserves'), v('total_assets')):
        c['equity<=assets'] = v('equity_cap') + v('reserves') + (v('borrowings') or 0) <= v('total_assets') * 1.001
    if v('eps') is not None and v('pat') is not None and abs(v('pat')) > 0.05 and v('eps') != 0:
        c['eps_sign'] = (v('eps') > 0) == (v('pat') > 0)
    big = max(abs(v('sales') or 0), abs(v('total_assets') or 0))
    if big:
        c['magnitude'] = [k for k in r if k not in ('eps', 'sales', 'total_assets') and abs(r[k][0]) > 3 * big] or True
    return c


CHECK_FIELDS = {'pbt-tax=pat': ['pbt', 'tax', 'pat'], 'opm_plausible': ['sales', 'pbt', 'interest', 'dep', 'other_income'],
                'sales_positive': ['sales'], 'equity<=assets': ['equity_cap', 'reserves', 'borrowings', 'total_assets'],
                'eps_sign': ['eps', 'pat'], 'magnitude': []}


def parse_pages(pgs, fy_hint=None, fym=3):
    """pgs: list of (page_no, text). -> result dict (bases with years, fields, checks, helper lists)."""
    found = {s: find(pgs, s) for s in ('bs', 'pl', 'cf')}
    out = {'bases': {}}
    heads = [t for _, t in pgs if any(stmt_head(t, s) for s in HEAD)] or \
        [t for _, t in pgs if any(re.search(HEAD[s], ' '.join(t[:2500].split()).upper()) for s in HEAD)]
    yend, months = report_year(heads)
    order = {pid: i for i, (pid, _) in enumerate(pgs)}
    starts = sorted(order[v[1]] for s in found for v in found[s].values())
    if yend is None and fy_hint:
        yend = dt.date(int(fy_hint), int(fym), 28)
        out['note_year'] = 'year not read from headings; taken from the link (a helper confirms it)'
    out['year_end'] = yend.isoformat()[:7] if yend else None
    out['months'] = months
    for basis in ('standalone', 'consolidated'):
        if basis not in found['pl'] and basis not in found['bs']:
            continue
        pick = {s: found[s].get(basis) for s in found}
        text_of = {p: t for p, t in pgs}
        units = {}  # each statement page's own unit (its head first, then the whole page)
        for s in pick:
            if pick[s]:
                units[s] = unit_of(text_of[pick[s][1]][:1500])
                if units[s][0] is None:
                    units[s] = unit_of(text_of[pick[s][1]])
        known = [u for u in units.values() if u[0] is not None]
        for s in units:
            if units[s][0] is None and known:  # a page without a unit word: the basis's other pages' unit
                units[s] = (known[0][0], known[0][1] + ' (from another statement page)')
        unit = all(u[0] is not None for u in units.values()) or None
        uword = {s: u[1] for s, u in units.items()}
        d = {s: ({k: ([None if x is None else x * units[s][0] for x in v] if k != 'eps' else v) for k, v in pick[s][2].items()}
                 if pick[s] and units[s][0] is not None else (pick[s][2] if pick[s] else {})) for s in pick}
        flags = {s: (pick[s][5] if pick[s] else {}) for s in pick}
        pages = {s: pick[s][1] if pick[s] else None for s in pick}
        pages.update({s + '_split': bool(pick[s] and pick[s][4]) for s in pick})
        if pages['bs']:
            bt = text_of[pages['bs']].lower()
            pages['bs_noloans'] = not re.search(r'borrowing|secured|loan funds|\bloans?\b(?! and advances| & advances)|'
                                                r'debenture|deposits', bt)
        if pages['pl'] and not any(k in d['pl'] for k in ('div_interim', 'div_final', 'div_plain', 'approp')):
            # dividend from the notes that follow this basis's P&L (new format: proposed dividend in the reserves note)
            a_ = order[pages['pl']]
            b_ = min([x for x in starts if x > a_ + 1] + [len(pgs)])
            for pid, t in pgs[a_ + 1:b_]:
                if any(stmt_head(t, s) for s in HEAD):
                    continue
                o_, n_, _, fl_ = parse_page(t, 'pl')
                uf = (units.get('pl') or (1,))[0] or 1  # notes in the P&L's unit
                got = {k: [None if x is None else x * uf for x in o_[k]] for k in ('div_interim', 'div_final') if k in o_}
                if got:
                    d['pl'] = dict(d['pl'], **got)
                    flags['pl'] = dict(flags['pl'], **{k: fl_.get(k, 'notes') for k in got})
                    pages['div_page'] = pid
                    break
        yrs, bank = derive(d['bs'], d['pl'], d['cf'], 1, flags, pages)  # already in crore
        if sum(len(y) for y in yrs) < 6:  # a heading match on a notes page, not a statement
            out.setdefault('notes', []).append(f'{basis}: heading found on pages {pages} but under 3 fields a year read; '
                                               'treated as not a statement')
            continue
        if unit is None:
            for y in yrs:
                for k in y:
                    y[k][1] = 'low'
        B = {'pages': {s: pages[s] for s in found}, 'unit': uword, 'bank': bank,
             'split_found': {s: pages[s + '_split'] for s in found}, 'raw': d, 'years': {},
             'notes': [n for s in pick if pick[s] for n in pick[s][3]] + ([] if unit else ['unit not found'])}
        for j, y in enumerate(yrs):
            ck = checks(y)
            need = NEED_BANK if bank else NEED
            helper = {f for f in need if f not in y or y[f][1] == 'low'} | \
                {f for k, ok in ck.items() if ok is False for f in CHECK_FIELDS[k] if f in need}
            if isinstance(ck.get('magnitude'), list):
                helper |= {f for f in ck['magnitude'] if f in need} | {'sales', 'total_assets'}
                ck['magnitude'] = False
            if len(helper) > len(need) / 2:  # mostly unread: the rest of this column isn't trusted either
                helper = set(need)
            if out.get('note_year'):
                helper.add('year_end')
            helper = sorted(helper)
            key = f'{(yend.year - j) if yend else "?"}-{yend.month:02d}' if yend else f'cur-{j}'
            B['years'][key] = {'fields': {k: [round(x[0], 4), x[1], x[2]] for k, x in y.items()}, 'checks': ck,
                               'helper': helper}
        out['bases'][basis] = B
    return out


# ------------------------------------------------------------------ links and downloads ------------------------------------
def load(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def names(sym):
    """BSE file-name variants from today's screener and BSE names (old names aren't known)."""
    raw = []
    ov = ((load(os.path.join(COMP, sym, 'scr', 'overview.json')) or {}).get('data') or {})
    if ov.get('name'):
        raw.append(ov['name'])
    p = os.path.join('data', 'market', 'bse_codes.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r['nse_symbol'] == sym and r.get('bse_name'):
                raw.append(r['bse_name'])
    out = []
    for nm in raw:
        nm = re.sub(r'\(.*?\)', '', nm).upper().replace('.', '').replace(',', '')
        nm = re.sub(r'\s+', ' ', nm).strip()
        nm = re.sub(r' LIMITED$', ' LTD', nm)
        if not nm.endswith(' LTD'):
            nm += ' LTD'
        base = nm.replace('-', ' ')
        for v in (nm, base, base.replace('&', 'AND'), base[:-4] + ' LIMITED', base.replace('&', 'AND')[:-4] + ' LIMITED',
                  re.sub(r'^THE ', '', base)):
            out.append(re.sub(r'\s+', '_', v.strip()))
    return list(dict.fromkeys(out))


LINKS = {}  # (sym, report year) -> url, from <run>/ar_links.csv (sym, fy, url): links found in BSE's list (browser pane)


def candidates(sym, ry, fym, code, docs):
    c = [('browser_list', LINKS[(sym, ry)])] if (sym, ry) in LINKS else []
    for x in docs:
        if str(x.get('year')) == str(ry) and x.get('url'):
            c.append(('screener_list', x['url']))
    if code:
        if ry >= 2010:
            c.append(('bseplus_guess', f'https://www.bseindia.com/bseplus/AnnualReport/{code}/{code}{fym:02d}{ry % 100:02d}.pdf'))
        if ry <= 2012:
            for nm in names(sym):
                c.append(('histannr_guess', f'https://www.bseindia.com/HIS_ANN_RPT/HISTANNR/{ry}/{nm}-{code}-MARCH-{ry}.PDF'))
    return c


def curl_get(url, out, timeout=600):
    try:
        r = subprocess.run(['curl.exe', '-s', '-L', '-m', str(timeout), '-o', out, '-w', '%{http_code}', url],
                           capture_output=True, text=True, timeout=timeout + 30)
        code = int((r.stdout.strip() or '0')[-3:])
    except (subprocess.TimeoutExpired, ValueError):
        code = 0
    if code != 200 or not os.path.exists(out):
        return None
    head = open(out, 'rb').read(8)
    if head.startswith(b'%PDF'):
        return out
    if head.startswith(b'PK'):  # NSE zips holding the PDF
        try:
            with zipfile.ZipFile(out) as z:
                pdfs = [n for n in z.namelist() if n.lower().endswith('.pdf')]
                if pdfs:
                    p = out + '.x.pdf'
                    open(p, 'wb').write(z.read(max(pdfs, key=lambda n: z.getinfo(n).file_size)))
                    return p
        except zipfile.BadZipFile:
            pass
    return None


def fy_folder(y):
    return f'FY{y % 100:02d}Q4'


def chart_check(sym, res, cache={}):
    """Sales against the chart's TTM sales 75 days after the year end (history.json, from 2005): when no basis is within
    25%, that year's sales go to a helper; a ratio near 10, 100, 1000 (or their inverse) means a wrong unit, so every
    field of that basis-year does."""
    import mb_features as mf
    if sym not in cache:
        cache.clear()
        cache[sym] = mf.Company(sym, COMP, chart_only=True)
    c = cache[sym]
    keys = {k for B in res.get('bases', {}).values() for k in B['years'] if re.match(r'\d{4}-\d\d$', k)}
    for k in keys:
        e = mf.month_end(int(k[:4]), int(k[5:]))
        cv = c.sales.lookup(e + dt.timedelta(days=75)) if c.sales.raw else None
        if not cv or cv <= 0:
            continue
        rs = {}
        for b, B in res['bases'].items():
            y = B['years'].get(k)
            if y and 'sales' in y['fields'] and y['fields']['sales'][0]:
                rs[b] = y['fields']['sales'][0] / cv
                y['chart_sales_ratio'] = round(rs[b], 3)
        if not rs or any(0.75 <= x <= 1.33 for x in rs.values()):
            continue
        for b, x in rs.items():
            y = res['bases'][b]['years'][k]
            unitlike = any(abs(x * 10 ** n - 1) < 0.15 for n in range(-7, 8) if n)
            add = [f for f in (NEED_BANK if res['bases'][b]['bank'] else NEED)] if unitlike else ['sales']
            y['helper'] = sorted(set(y['helper']) | set(add))
            y['checks']['chart_sales'] = False
            res['bases'][b]['notes'].append(f'{k} sales {x:.2f}x the chart TTM sales' + (' (unit?)' if unitlike else ''))
    return res


def save_report(sym, pgs, keep, url, src, ry, fym):
    """Save the statement pages and parsed JSON; returns (result dict, json path, pages path)."""
    sel = [pgs[i] for i in sorted(keep)]
    res = chart_check(sym, parse_pages(sel, ry, fym))
    y = int(res['year_end'][:4]) if res.get('year_end') else ry
    d = os.path.join(COMP, sym, fy_folder(y))
    os.makedirs(d, exist_ok=True)
    pf = os.path.join(d, f'ar_FY{y % 100:02d}_pages.txt')
    with open(pf, 'w', encoding='utf-8') as fh:
        for n, t in sel:
            fh.write(f'=== page {n} ===\n{t}\n')
    res.update(sym=sym, url=url, src=src, link_year=ry, pages_file=pf.replace('\\', '/'), n_pages_pdf=len(pgs),
               parsed_at=dt.datetime.now().isoformat(timespec='seconds'))
    if res.get('year_end') and y != ry:
        res['note_link_year'] = f'link year {ry}, statements are for {res["year_end"]}'
    jf = os.path.join(d, f'ar_FY{y % 100:02d}.json')
    json.dump(res, open(jf, 'w', encoding='utf-8'), indent=1)
    return res, jf, pf


def read_pages_file(pf):
    pgs, cur, buf = [], None, []
    for line in open(pf, encoding='utf-8').read().split('\n'):
        m = re.match(r'=== page (\d+[LR]?) ===$', line)
        if m:
            if cur is not None:
                pgs.append((cur, '\n'.join(buf)))
            cur, buf = m.group(1), []
        else:
            buf.append(line)
    if cur is not None:
        pgs.append((cur, '\n'.join(buf)))
    return pgs


# ------------------------------------------------------------------ reading back (mb_features) -----------------------------
def load_ar(sym, root=COMP):
    """{basis: {year_end 'YYYY-MM': {'fields': {f: (value, conf, src)}, 'months', 'report', 'has_consolidated'}}}.
    Each year from the report whose current year it is (as filed) when there is one, else from the next report's
    previous-year column. Helper values (ar_FYyy_helper.json) override parsed ones; parsed values flagged for a helper
    (or low confidence) are left out until the helper answers."""
    out = {'consolidated': {}, 'standalone': {}}
    rank = {}
    for jf in sorted(glob.glob(os.path.join(root, sym, 'FY*Q4', 'ar_FY*.json'))):
        if jf.endswith('_helper.json'):
            continue
        r = load(jf) or {}
        hp = load(jf[:-5] + '_helper.json') or {}
        if hp.get('wrong_report'):
            continue
        rep = os.path.basename(jf)[3:-5]
        has_c = 'consolidated' in (r.get('bases') or {}) or 'consolidated' in (hp.get('bases') or {})
        for basis in ('consolidated', 'standalone'):
            yrs = dict(((r.get('bases') or {}).get(basis) or {}).get('years') or {})
            if hp.get('replace_parsed'):  # the helper re-read the whole report (wrong year, wrong pages, scanned)
                yrs = {}
            for k in ((hp.get('bases') or {}).get(basis) or {}):
                yrs.setdefault(k, {'fields': {}})
            for j, (key, y) in enumerate(sorted(yrs.items(), reverse=True)):
                if not re.match(r'\d{4}-\d\d$', key):
                    continue
                cur = key == (hp.get('year_end') or r.get('year_end') or '')
                f = {k: (v[0], v[1], 'ar') for k, v in (y.get('fields') or {}).items()
                     if v[1] != 'low' and k not in (y.get('helper') or [])}  # flagged fields wait for the helper
                hv = ((hp.get('bases') or {}).get(basis) or {}).get(key) or {}
                for k, v in hv.items():
                    if k in FIELDS and isinstance(v, (int, float)):
                        f[k] = (float(v), 'helper', 'ar_helper')
                    elif k in FIELDS and v is None:
                        f.pop(k, None)  # the helper found the field isn't on the page
                if isinstance(hv.get('other_income'), (int, float)) and isinstance(hv.get('exceptional'), (int, float)):
                    f['other_income'] = (hv['other_income'] + hv['exceptional'], 'helper', 'ar_helper')  # screener's way
                if 'op' not in f or f['op'][1] != 'helper':  # recompute op from final components
                    c = [f.get(k) for k in ('pbt', 'interest', 'dep', 'other_income')]
                    if None not in c and not (((r.get('bases') or {}).get(basis) or {}).get('bank')):
                        f['op'] = (c[0][0] + c[1][0] + c[2][0] - c[3][0], 'derived', 'ar')
                    else:
                        f.pop('op', None)
                pr = (1 if cur else 0)
                if key not in out[basis] or pr > rank.get((basis, key), -1):
                    out[basis][key] = {'fields': f, 'months': r.get('months', 12) if cur else 12, 'report': rep,
                                       'has_consolidated': has_c,
                                       'bank': bool(((r.get('bases') or {}).get(basis) or {}).get('bank'))}
                    rank[(basis, key)] = pr
    return out


# ------------------------------------------------------------------ plan ---------------------------------------------------
def plan(a):
    import mb_features as mf
    from bse_shp import bse_code
    D = hist_dir()
    rows_f = a.rows or os.path.join(D, 'sample_candidates.csv')
    groups = set(a.groups.split(',')) if a.groups else None
    rows = [r for r in csv.DictReader(open(rows_f, encoding='utf-8')) if not groups or r.get('group') in groups]
    need, info, rows_need, stat = collections.defaultdict(set), {}, collections.defaultdict(list), collections.Counter()
    for r in rows:
        s, asof = r['sym'], dt.date.fromisoformat((r.get('as_of') or r['start'])[:10])
        if s not in info:
            c = mf.Company(s, COMP)
            yrs = set()
            for b in ('consolidated', 'standalone'):
                t = c.st['profit_loss'][b]
                yrs |= {e.year for e, m in t.months.items() if m == 12 and any(v is not None for v in t.cols[e].values())}
            info[s] = dict(fym=c.fy_month, scr=yrs, first_px=c.px[0][0] if c.px else None, code=bse_code(s, COMP) or '')
        I = info[s]
        fym = I['fym']
        y0 = asof.year if mf.month_end(asof.year, fym) + dt.timedelta(days=60) <= asof else asof.year - 1
        if mf.month_end(y0, fym) + dt.timedelta(days=60) > asof:
            y0 -= 1
        yrs = set(range(y0 - 4, y0 + 1))
        if mf.month_end(y0, fym) + dt.timedelta(days=180) > asof:
            yrs.add(y0 - 5)
        first = min(I['scr']) if I['scr'] else 9999
        gap = {y for y in yrs if y < first}
        lst = I['first_px'].year if I['first_px'] and I['first_px'].year > 2005 else None  # charts start Jan 2005
        pre = {y for y in gap if lst and y < lst - 1}
        stat['rows'] += 1
        stat['rows_with_gap'] += bool(gap - pre)
        stat['gap_years'] += len(gap)
        stat['pre_listing_years'] += len(pre)
        need[s] |= gap - pre
        for y in gap - pre:
            rows_need[(s, y)].append(asof.isoformat())
    out = []
    for s in sorted(need):
        for y in sorted(need[s], reverse=True):
            out.append(dict(sym=s, fy=y, fym=info[s]['fym'], code=info[s]['code'], scr_first=min(info[s]['scr'] or {0}),
                            rows=' '.join(sorted(set(rows_need[(s, y)])))))
    p = os.path.join(D, 'ar_plan.csv')
    w = csv.DictWriter(open(p, 'w', newline='', encoding='utf-8'), fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
    print(dict(stat), '| companies', len(need), '| needed years', len(out), '->', p)


# ------------------------------------------------------------------ fetch --------------------------------------------------
def read_status(D):
    p = os.path.join(D, 'ar_status.csv')
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def append_status(D, row):
    p = os.path.join(D, 'ar_status.csv')
    new = not os.path.exists(p)
    with open(p, 'a', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=STATUS_COLS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, '') for k in STATUS_COLS})


def covered_years(sym):
    """Fiscal years (int) whose figures a saved report gives (current or previous column), any basis."""
    got = set()
    for jf in glob.glob(os.path.join(COMP, sym, 'FY*Q4', 'ar_FY*.json')):
        if jf.endswith('_helper.json'):
            continue
        r = load(jf) or {}
        for b in (r.get('bases') or {}).values():
            got |= {int(k[:4]) for k in b.get('years', {}) if re.match(r'\d{4}-', k)}
    return got


def result_of(res):
    if not res.get('bases'):
        return 'needs-helper', 'no statement pages found by heading'
    h = any(y['helper'] for b in res['bases'].values() for y in b['years'].values())
    return ('needs-helper' if h else 'parsed'), ''


def helper_summary(res, want):
    """'basis:YYYY-MM:f1|f2; ...' for the years wanted."""
    parts = []
    for b, B in (res.get('bases') or {}).items():
        for k, y in B['years'].items():
            if y['helper'] and (not want or not k[:4].isdigit() or int(k[:4]) in want):
                parts.append(f'{b[0]}:{k}:{"|".join(y["helper"])}')
    return '; '.join(parts)


def get_report(sym, ry, fym, code, docs, gap, tmp, D, want):
    """Try the candidate links for report year ry; save and log. -> status row."""
    cands = candidates(sym, ry, fym, code, docs)
    row = dict(sym=sym, report_fy=ry, fym=fym, code=code, at=dt.datetime.now().isoformat(timespec='seconds'))
    if not cands:
        row.update(result='not-found', note='no link and no BSE code')
        return row
    tried = []
    for src, url in cands:
        d = tempfile.mkdtemp(prefix=f'ar_{sym}_{ry}_', dir=tmp)
        try:
            f = curl_get(url, os.path.join(d, 'r.bin'))
            time.sleep(gap)
            tried.append(src)
            if not f:
                continue
            row.update(src=src, url=url, mb=round(os.path.getsize(f) / 1e6, 1))
            if KEEP_PDF:
                os.makedirs(KEEP_PDF, exist_ok=True)
                shutil.copy(f, os.path.join(KEEP_PDF, f'{sym}_{ry}.pdf'))
            pgs = pdf_pages(f)
            if len(re.sub(r'\s', '', ' '.join(t for _, t in pgs))) < 40 * max(1, len(pgs)):
                row.update(result='scanned', note=f'no text layer ({len(pgs)} pages); needs OCR or a helper reading the PDF')
                d_ = os.path.join(COMP, sym, fy_folder(ry))
                os.makedirs(d_, exist_ok=True)
                jf = os.path.join(d_, f'ar_FY{ry % 100:02d}.json')  # stub, so the helper's answer sits beside a report file
                json.dump(dict(sym=sym, url=url, src=src, link_year=ry, year_end=None, months=12, bases={}, scanned=True,
                               n_pages_pdf=len(pgs), parsed_at=dt.datetime.now().isoformat(timespec='seconds')),
                          open(jf, 'w', encoding='utf-8'), indent=1)
                row.update(json_file=jf.replace('\\', '/'))
                return row
            hit = stmt_pages(pgs)
            keep = set()
            for i in hit:
                keep |= {i, i + 1} if i + 1 < len(pgs) else {i}
            if not keep:  # no statement heading recognised: keep the whole text so a helper can find the statements
                keep = set(range(len(pgs)))
            dpg = [i for i, (_, t) in enumerate(pgs) if re.search(r'(?im)^\s*(proposed|final|interim)\s+(final\s+)?(equity\s+)?'
                                                               r'dividends?\b(?!.*(tax|per share|preference)).*\d', t)]
            keep |= set(dpg[:8])  # notes holding the proposed dividend (new format)
            res, jf, pf = save_report(sym, pgs, keep, url, src, ry, fym)
            result, note = result_of(res)
            row.update(result=result, years=' '.join(sorted({k for b in res['bases'].values() for k in b['years']})),
                       bases=' '.join(res['bases']), helper_fields=helper_summary(res, want),
                       pages_file=pf.replace('\\', '/'), json_file=jf.replace('\\', '/'),
                       note='; '.join(x for x in (note, res.get('note_link_year', ''), res.get('note_year', '')) if x))
            return row
        finally:
            shutil.rmtree(d, ignore_errors=True)
    row.update(result='not-found', note='tried ' + ','.join(dict.fromkeys(tried)))
    return row


def fetch(a):
    D = hist_dir()
    pl = list(csv.DictReader(open(os.path.join(D, 'ar_plan.csv'), encoding='utf-8')))
    if a.syms:
        keep = set(a.syms.split(','))
        pl = [r for r in pl if r['sym'] in keep]
    done = {(r['sym'], int(r['report_fy'])): r for r in read_status(D)}
    lf = os.path.join(D, 'ar_links.csv')
    if os.path.exists(lf):
        for r in csv.DictReader(open(lf, encoding='utf-8')):
            LINKS[(r['sym'], int(r['fy']))] = r['url']
            if done.get((r['sym'], int(r['fy'])), {}).get('result') == 'not-found':
                del done[(r['sym'], int(r['fy']))]  # try again with the new link
    by = collections.defaultdict(list)
    for r in pl:
        by[r['sym']].append(r)
    tmp = a.tmp or tempfile.gettempdir()
    os.makedirs(tmp, exist_ok=True)
    t0, n = time.time(), 0
    for k, (sym, rs) in enumerate(sorted(by.items())):
        need = sorted({int(r['fy']) for r in rs}, reverse=True)
        scr_first = int(rs[0]['scr_first'] or 0)
        fym, code = int(rs[0]['fym']), rs[0]['code']
        docs = ((load(os.path.join(COMP, sym, 'scr', 'documents.json')) or {}).get('data') or {}).get('annual_reports') or []
        got = covered_years(sym)
        for y in need:
            if y in got:
                continue
            for ry in (y, y + 1):
                if (sym, ry) in done:
                    continue
                row = get_report(sym, ry, fym, code, docs, a.gap, tmp, D, set(need))
                append_status(D, row)
                done[(sym, ry)] = row
                n += 1
                got = covered_years(sym)
                if y in got:
                    break
        if k % 10 == 0:
            print(f'{k + 1}/{len(by)} companies, {n} reports tried, {time.time() - t0:.0f}s', flush=True)
    print(f'done: {len(by)} companies, {n} reports tried, {time.time() - t0:.0f}s')


def reparse(a):
    D = hist_dir()
    keep = set(a.syms.split(',')) if a.syms else None
    rows = read_status(D)
    plan_need = collections.defaultdict(set)
    for r in csv.DictReader(open(os.path.join(D, 'ar_plan.csv'), encoding='utf-8')):
        plan_need[r['sym']].add(int(r['fy']))
    out = []
    for r in rows:
        if r['pages_file'] and (not keep or r['sym'] in keep) and os.path.exists(r['pages_file']):
            old = load(r['json_file']) or {}
            pgs = read_pages_file(r['pages_file'])
            res = chart_check(r['sym'], parse_pages(pgs, int(r['report_fy']), int(r['fym'] or 3)))
            for k in ('sym', 'url', 'src', 'link_year', 'pages_file', 'n_pages_pdf'):
                res[k] = old.get(k)
            res['parsed_at'] = dt.datetime.now().isoformat(timespec='seconds')
            y = int(res['year_end'][:4]) if res.get('year_end') else int(r['report_fy'])
            jf = os.path.join(COMP, r['sym'], fy_folder(y), f'ar_FY{y % 100:02d}.json')
            if jf.replace('\\', '/') != r['json_file'] and os.path.exists(r['json_file']):
                os.remove(r['json_file'])
            os.makedirs(os.path.dirname(jf), exist_ok=True)
            json.dump(res, open(jf, 'w', encoding='utf-8'), indent=1)
            result, note = result_of(res)
            r.update(result=result, years=' '.join(sorted({k for b in res['bases'].values() for k in b['years']})),
                     bases=' '.join(res['bases']), helper_fields=helper_summary(res, plan_need[r['sym']]),
                     json_file=jf.replace('\\', '/'))
        out.append(r)
    with open(os.path.join(D, 'ar_status.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=STATUS_COLS)
        w.writeheader()
        w.writerows(out)
    print('reparsed', sum(1 for r in out if r['pages_file']), collections.Counter(r['result'] for r in out))


# ------------------------------------------------------------------ queue ---------------------------------------------------
def cross_check(sym):
    """Across one company's reports: the same year read from two reports (current column of its own report, previous
    column of the next), and consecutive years, should not differ by a power of ten in sales, PAT or total assets (a wrong
    unit, which pre-2005 years can't be checked against the chart for). Offending basis-years go wholly to a helper;
    the flags are written into the reports' JSON (checks.cross_unit). Returns the number of basis-years flagged."""
    reps = []
    for jf in glob.glob(os.path.join(COMP, sym, 'FY*Q4', 'ar_FY*.json')):
        if not jf.endswith('_helper.json'):
            reps.append((jf, load(jf) or {}))
    vals = collections.defaultdict(list)  # (basis, year key) -> [(jf, field values)]
    for jf, r in reps:
        for b, B in (r.get('bases') or {}).items():
            for k, y in B['years'].items():
                if re.match(r'\d{4}-\d\d$', k):
                    vals[(b, k)].append((jf, {f: v[0] for f, v in y['fields'].items()}))
    p10 = lambda x: x and x > 0 and any(abs(x * 10 ** n - 1) < 0.2 for n in range(-7, 8) if n)
    bad = set()
    for (b, k), vs in vals.items():
        nxt = (b, f'{int(k[:4]) + 1}{k[4:]}')
        pairs = [(x, y) for i, x in enumerate(vs) for y in vs[i + 1:]] + \
                [(x, y) for x in vs for y in vals.get(nxt, [])]  # same year twice; consecutive years
        for (j1, f1), (j2, f2) in pairs:
            for f in ('sales', 'pat', 'total_assets'):
                if f1.get(f) and f2.get(f) and p10(abs(f1[f] / f2[f])):
                    bad |= {(j1, b, k), (j2, b, k if (j2, f2) in vs else nxt[1])}
    for jf, r in reps:
        hit = [(b, k) for (j, b, k) in bad if j == jf]
        if not hit:
            continue
        for b, k in hit:
            y = r['bases'][b]['years'][k]
            y['checks']['cross_unit'] = False
            y['helper'] = sorted(set(y['helper']) | set(NEED_BANK if r['bases'][b].get('bank') else NEED))
        json.dump(r, open(jf, 'w', encoding='utf-8'), indent=1)
    return len(bad)


def queue(a):
    """ar_missing.csv: needed years with no report found (report y and y+1 both not found; the browser pane's BSE list
    finds them). ar_helper_queue.csv: reports with fields a helper must read, for needed years only; a year's previous-year
    column in the next report is skipped when the year's own report exists (the helper reads that one). Runs cross_check
    on every company first."""
    D = hist_dir()
    pl = list(csv.DictReader(open(os.path.join(D, 'ar_plan.csv'), encoding='utf-8')))
    st = read_status(D)
    nx = sum(cross_check(s) for s in sorted({r['sym'] for r in pl}))
    print('cross-report unit check: basis-years flagged', nx)
    tried = collections.defaultdict(dict)
    for r in st:
        tried[r['sym']][int(r['report_fy'])] = r
    missing, hq = [], []
    for sym in sorted({r['sym'] for r in pl}):
        need = {int(r['fy']) for r in pl if r['sym'] == sym}
        got = covered_years(sym)
        code = next(r['code'] for r in pl if r['sym'] == sym)
        found = lambda ry: tried[sym].get(ry, {}).get('result') in ('parsed', 'needs-helper', 'scanned')
        for y in sorted(need - got):
            if found(y) or found(y + 1):
                continue  # a report is there (scanned or unread): the helper queue has it
            why = []
            for ry in (y, y + 1):
                t = tried[sym].get(ry)
                if t:
                    why.append(f'report FY{ry % 100:02d}: {t["result"]}' + (f' ({t["note"]})' if t['note'] else ''))
            missing.append(dict(sym=sym, bse_code=code, fy=y, why='; '.join(why) or 'not tried'))
        own = set()  # (basis, year) that have their own report
        reps = {}
        for ry, t in tried[sym].items():
            if t['json_file'] and os.path.exists(t['json_file']):
                res = load(t['json_file']) or {}
                reps[ry] = res
                for b in (res.get('bases') or {}):
                    if res.get('year_end'):
                        own.add((b, res['year_end']))
        for ry, t in sorted(tried[sym].items()):
            res = reps.get(ry)
            if t['result'] == 'needs-helper' and res is not None:
                parts = []
                for b, B in (res.get('bases') or {}).items():
                    for k, y in B['years'].items():
                        if not y['helper'] or (k[:4].isdigit() and int(k[:4]) not in need):
                            continue
                        if k != res.get('year_end') and (b, k) in own:
                            continue
                        parts.append(f'{b[0]}:{k}:{"|".join(y["helper"])}')
                if parts or not res.get('bases'):
                    hq.append(dict(sym=sym, fy=int(res['year_end'][:4]) if res.get('year_end') else ry,
                                   fields='; '.join(parts) or 'all (no statement pages found by heading: full text saved)',
                                   page_text=t['pages_file'], json=t['json_file'], url=t['url'],
                                   helper_file=t['json_file'][:-5] + '_helper.json'))
            elif t['result'] == 'scanned':
                jf = t['json_file'] or os.path.join(COMP, sym, fy_folder(ry), f'ar_FY{ry % 100:02d}.json').replace('\\', '/')
                if not os.path.exists(jf):  # stub for scanned reports logged before stubs were written
                    os.makedirs(os.path.dirname(jf), exist_ok=True)
                    json.dump(dict(sym=sym, url=t['url'], src=t['src'], link_year=ry, year_end=None, months=12, bases={},
                                   scanned=True), open(jf, 'w', encoding='utf-8'), indent=1)
                hq.append(dict(sym=sym, fy=ry, fields='all (scanned PDF, no text layer: read it from the url)',
                               page_text='', json=jf, url=t['url'], helper_file=jf[:-5] + '_helper.json'))
    hq = [h for h in hq if not os.path.exists(h['helper_file'])]  # answered already
    for i, h in enumerate(hq):
        h['group'] = i // a.per + 1
    for name, rows, cols in (('ar_missing.csv', missing, ['sym', 'bse_code', 'fy', 'why']),
                             ('ar_helper_queue.csv', hq, ['group', 'sym', 'fy', 'fields', 'page_text', 'json', 'url',
                                                          'helper_file'])):
        with open(os.path.join(D, name), 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    c = collections.Counter(r['result'] for r in st)
    print(f'plan years {len(pl)}; reports tried {len(st)} {dict(c)}; missing years {len(missing)} '
          f'({len({m["sym"] for m in missing})} companies); helper queue {len(hq)} reports in '
          f'{(len(hq) + a.per - 1) // a.per} groups')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'fetch', 'reparse', 'queue', 'parse'])
    ap.add_argument('file', nargs='?')
    ap.add_argument('--rows')
    ap.add_argument('--groups', default='winner,fallen_winner')
    ap.add_argument('--syms')
    ap.add_argument('--gap', type=float, default=1.5)
    ap.add_argument('--tmp')
    ap.add_argument('--per', type=int, default=25)
    ap.add_argument('--fy', type=int)
    ap.add_argument('--keep-pdf')
    a = ap.parse_args()
    global KEEP_PDF
    KEEP_PDF = a.keep_pdf
    if a.cmd == 'plan':
        plan(a)
    elif a.cmd == 'fetch':
        fetch(a)
    elif a.cmd == 'reparse':
        reparse(a)
    elif a.cmd == 'queue':
        queue(a)
    else:
        if a.file.lower().endswith('.txt'):
            pgs = read_pages_file(a.file)
        else:
            pp = pdf_pages(a.file)
            pgs = [pp[i] for i in sorted({j for i in stmt_pages(pp) for j in (i, i + 1) if j < len(pp)} |
                                         {i for i, (_, t) in enumerate(pp) if re.search(r'(?im)^\s*proposed\s+(final\s+)?'
                                                                                         r'(equity\s+)?dividend.*\d', t)})]
        r = parse_pages(pgs, a.fy)
        print('year_end', r.get('year_end'), 'months', r.get('months'))
        for b, v in r['bases'].items():
            print(b, v['pages'], v['unit'], v['split_found'], 'bank' if v['bank'] else '')
            for k, y in v['years'].items():
                print('  ', k, {f: (round(x[0], 2), x[1][0]) for f, x in y['fields'].items()})
                print('     checks', {c: ok for c, ok in y['checks'].items() if ok is not True}, 'helper', y['helper'])
            if v['notes']:
                print('   notes', v['notes'][:6])


if __name__ == '__main__':
    main()
