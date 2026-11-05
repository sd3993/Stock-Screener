import argparse, collections, csv, datetime as dt, glob, json, os, re, shutil, subprocess, sys, tempfile, time, zipfile
# Multibagger study (process/past/p4_statements.md, p8_features.md): annual statements for the years before screener's
# statements (screener has ~12 years), read from the annual reports. Plain curl with its default identity; no model tokens.
#   python -I tools/scripts/ar_statements.py plan  [--rows FILE] [--groups winner,fallen_winner]   -> <run>/ar_plan.csv
#   python -I tools/scripts/ar_statements.py fetch [--gap 1.5] [--syms A,B] [--tmp DIR]   download, extract, parse (resumable)
#   python -I tools/scripts/ar_statements.py reparse [--syms A,B]   re-parse the saved page text (after a parser fix)
#   python -I tools/scripts/ar_statements.py refetch [--syms A,B] [--dry] [--gap 1.5]   download again (recorded url) the reports
#     whose saved pages lack a balance sheet / P&L / cash flow for some basis (or any statement), with the current page selection
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
#   ar_FY<yy>_helper.json  written by a fallback helper (process/past/p7_ar_helpers.md); overrides parsed fields
# Fields (screener's definitions): sales (net of excise; banks: interest earned), other_income (incl. exceptional items),
#   interest, dep, pbt, tax, pat (before minority interest), eps (basic, as reported), dividend (proposed/paid on equity,
#   excl. tax), op (= pbt + interest + dep - other_income), equity_cap, reserves (incl. share warrants), borrowings (all
#   loans; banks: deposits too), total_assets (old Schedule VI: funds employed + current liabilities and provisions),
#   debtors, cfo. Helpers get a field when it is missing, when two values land on one year's side, or a check fails.
# Status: <run>/ar_status.csv, one row per report tried (parsed / needs-helper / not-found / scanned / error).
# Other income and operating profit are classified differently from screener's old data: mb_features.py keeps report and
# screener years apart in margin trends.
# Learned from the first 352 reports (what fails, and how the parser reads it; 'reparse' re-runs these on saved pages):
#   - Year split: with an odd number of value columns the header-year gap can be wrong when the text is jittered; the gap
#     that puts as many numbers left as right on the most lines wins (split_at). Without header years it stays None.
#   - Two numbers on a side: a 1-2 digit note/schedule number first on a side is dropped; 'Secured / Unsecured (+ subtotal)'
#     and 'Reserves (+ capital = shareholders' funds)' lines keep the inner figure when outer = inner + the line above (the
#     old read double-counted loans); 'Sales / Less: excise, net' reads the net; a dash just left of the split with more
#     numbers left than right belongs to the right side; Rs + USD columns: the Rs column (the first when Rs is named first).
#   - Sales with an unusual label ('Earnings from sale of electricity', 'Gross contract receipts', 'Revenues'): the lines
#     above 'Other income' that add up with it to the total under it (sum_income, checked to the rounding). 'Sales tax' is
#     an expense, not sales; a plain 'Turnover' is the net when 'Gross turnover' is also there.
#   - Profit lines: 'Profit for the year' is often before tax; 'Profit after tax' (last one that names tax, not 'before')
#     is the profit; with discontinued operations only an '(A+B)' total counts (else flagged); an EPS line that names its
#     profit ('computed on ... profit for the year') is not a profit line; 'Profit before tax and exceptional items' is the
#     PBT only when the page has no exceptional item.
#   - Margin check (opm_plausible) is waived when the face of the P&L foots (income total - expenses total = profit line).
#   - Cash flow: pages found by content (operating + investing activities), not only by heading; a headingless page takes
#     the basis of the statement page just before it; one headed by another company (a subsidiary's accounts in the same
#     report; entity()) or >150 PDF pages from the P&L is ignored; the last 'net cash from operating activities' line wins
#     ('before extraordinary items' lines are skipped); 'Net cash generated / used - operating' is read (clean_label keeps
#     only the part after a ' / ').
#   - Units: ' ‘000’ with typographic quotes, '(Rs. ‘000)', '` ’ 000' are thousands. A headingless/unit-less page still
#     takes the unit of the basis's other statement pages.
# Second pass (4 Nov 2026; every change below was tested by 'reparse' against the first pass: trusted fields identical except
# where the old value was wrong, e.g. a subsidiary's page or a wrong unit):
#   - Ligatures (fi, fl ...) are expanded; 'T O T A L' spaced letters are joined; blank lines no longer reset a wrapped label
#     (a label wrapped over two lines is read as one when neither half matches; a bare 'Dividend' heading + 'Interim' / 'Final'
#     lines); section captions ('INCOME', 'APPROPRIATIONS', 'LOAN FUNDS' ...) in the label column are stripped.
#   - Wrong company's pages: the page's company name (entity(), cut at ' - CONSOLIDATED ...', '(Formerly ...)' skipped) is
#     compared with today's screener / BSE names (company_names()); with a page at >= 0.95, pages under 0.85 (subsidiaries'
#     statements printed in the same report) are dropped. Fixed ~25 reports read from a subsidiary's page.
#   - A two-up spread is cut only when both halves carry figures (a P&L with labels left and figures right under a centred
#     heading is one page); saved L/R pages are put back together by respread() on reparse.
#   - Previous-year column LEFT of the labels (BANARISUG): left_layout() rewrites the lines as 'label current previous' when
#     the header dates confirm the order (unlabeled subtotal lines too).
#   - Headings: a second pass with looser headings ('Consolidated Balance Sheet' with the date on the next line, 'Profit and
#     Loss Statement') only for a basis the strict headings found nothing for, then a third pass by content (content_pages()).
#     keep_pages() saves the pages by all three plus every cash flow page, so a 'refetch' of the 123 reports with a missing
#     statement (done 4 Nov 2026, 850 s, default gap) recovered the consolidated P&L / balance sheets that headings had missed.
#   - Dividend: 'Total dividend', 'first/second interim dividend', 'provision for proposed dividend'; a consolidated year takes
#     the standalone year's dividend of the same report (the company's); 'no dividend recommended' in the directors' report = 0
#     for the current year (not when an interim dividend is mentioned); an appropriation section without a dividend line is a
#     nil only when the page does not mention dividend at all (it used to be assumed nil).
#   - Banks: PBT = 'Net profit before taxes' from the cash flow statement, tax = PBT - net profit (0 <= tax <= 60% of PBT).
#   - Absent items: a complete P&L (PBT and PAT read, >= 12 lines) with no mention of interest / depreciation / per-share on the
#     page leaves that field out of the helper list (checks the page, y['absent']): a helper could only answer 'not on the page'.
#   - Units: whole-rupee units are dropped when most figures are small numbers with decimals (INFY consolidated, APOLLOTYRE);
#     statements with no unit word at all take the standard unit whose ratio to the chart's TTM sales fits every year (crore
#     itself included), or the unit of the same year in another report (cross_check). A cash flow in another unit than the
#     balance sheet is kept (it is legitimate); only a magnitude failure of cfo alone goes to a helper, not the whole year.
#   - Sales vs chart: the chart (TTM sales of the quarterly results, standalone before FY20 for many companies) was wrong in
#     the 1.3-2x cases where the P&L's total income line equals sales + other income (y['sales_ok']); those are no longer sent.
#     Unit-like ratios (10^n) still send every field of the basis-year.
#   - Cross-report check: two or more fields (of sales, PAT, total assets, reserves, equity capital) off by the same power of
#     ten = unit error (whole basis-year); one field off while others agree = that field only (same year), or ignored
#     (consecutive years, real growth) unless a 100x change in sales / total assets. 87 -> ~48 basis-years.
#   - First year of a company: a report with one value column gives one year (no empty previous-year column).
#   - Still for helpers: bank pbt/tax where the cash flow starts elsewhere, dividends only in the directors' report tables,
#     scanned PDFs (18), reports whose statements are not in the text layer, garbled/OCR text (jittered columns), statements of
#     several entities on one page, sales with no 'sales' label (contract income ...), and whatever the chart / cross-report
#     checks flag. Counts after the second pass: see the helper queue ('queue' prints them).
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
UNIT = [(r'crores?|cr\.', 1.0), (r'lakhs?|lacs?', 0.01), (r'millions?|mn\b', 0.1), (r"thousands?|['’‘]\s*000", 1e-4)]
NUM = re.compile(r'(\(-\)\s*|-\s?)?\(?\d[\d,]*(\.\d+)?\)?(?=\s|$)|(?<=\s)[—–-](?=\s|$)')
HEAD = {'bs': r'BALANCE\s*SHEET\s*AS\s*(A[TS]|ON)',
        'pl': r'PROFIT\s*(AND|&)\s*LOSS\s*(ACCOUNT|STATEMENT)?\s*FOR|STATEMENT\s*OF\s*PROFIT\s*(AND|&)\s*LOSS|'
              r'PROFIT\s*(AND|&)\s*LOSS\s*ACCOUNT',
        'cf': r'CASH\s*-?\s*FLOW\s*STATEMENT|STATEMENT\s*OF\s*CASH\s*-?\s*FLOWS?'}
HEAD_LOOSE = {'bs': r'BALANCE\s*SHEET\b(?!\s*ABSTRACT)',  # second pass, for a basis the strict headings found no page for
              'pl': r'PROFIT\s*(AND|&)\s*LOSS\s*(ACCOUNT|STATEMENT)?\s*FOR|STATEMENT\s*OF\s*PROFIT\s*(AND|&)\s*LOSS|'
                    r'PROFIT\s*(AND|&)\s*LOSS\s*(ACCOUNT|STATEMENT)'}
F = {  # field: label regexes (lower-case label, schedule refs removed); first matching line wins unless noted
    'bs': [('share_capital', r'^(equity )?share capital|^capital$'),
           ('warrants', r'share warrants|money received against share warrants'),
           ('reserves', r'^reserves? (and|&) surplus|^other equity'),
           ('minority', r'^minority interest'),
           ('dtl', r'^deferred tax liabilit(y|ies)( \(net\))?$'),
           ('secured', r'^secured loans'), ('unsecured', r'^unsecured loans'),
           ('lt_borr', r'^long[- ]term borrowings'), ('st_borr', r'^short[- ]term borrowings'),
           ('borr', r'^borrowings'), ('deposits', r'^deposits\b'),
           ('debtors', r'^(sundry |trade |book )?(debtors|receivables)\b(?!.*financ)|^trade and other receivables'),
           ('cl', r'^current liabilities$|^liabilities$'), ('prov', r'^provisions$'),
           ('total', r'^total\b|total funds employed|^total (equity and liabilities|assets)')],
    'pl': [('net_ops', r'^net income from operations|^revenue from operations \(net\)|^total revenue from operations'),
           ('net_sales', r'^net (sales|income from operations|revenue from operations|turnover)|^revenue from operations \(net\)|^sales \(net\)'),
           ('turnover', r'^turnover$'),
           ('gross_sales', r'^(gross )?(sales|income from operations?|revenue from operations?|turnover)\b(?!\s*(tax|promotion|commission|expens|(and|&) (marketing|distribution|selling)))'),
           ('excise', r'excise duty'),
           ('int_earned', r'interest ear[nh]ed'), ('int_expended', r'interest expended'),
           ('other_income', r'^other income'), ('int_income', r'^(add:? )?interest income'),
           ('total_income', r'^total (income|revenue)( \([^)]*\))?$'),
           ('total_exp', r'^total (expenses|expenditure|costs?)$'),
           ('pat_pre_mi', r'before minority interest|before share of (profit|loss)'),
           ('interest', r'^(less:? )?(interest|finance (costs?|charges|expenses)|financial (costs?|charges|expenses))(?!.*(income|received|earned))'),
           ('dep', r'^(less:? )?depreciation'),
           ('exceptional', r'^exceptional items?\b'),
           ('pbt', r'profit.*before (tax|taxes|taxation)$|profit.*before (tax|taxes|taxation)\b(?!.*exceptional)|before tax(es|ation)?$|'
                   r'^profit after exceptional items$'),
           ('pbt_pre_exc', r'before (tax|taxes|taxation) and (exceptional|extraordinary)|before (exceptional|extraordinary).*(tax|taxes|taxation)'),
           ('tax_total', r'^total tax(ation)?( expenses?)?$|^tax expenses?$|^total (provision for )?tax|^total income tax'),
           ('tax', r'^(provision for )?(tax|taxes|taxation|income tax)(?!.*dividend)'),
           ('pat', r'^net profit|profit (for the (year|period)|after ?tax(ation)?)\b|loss after tax|profit/?\s*\(?(-\)\s*)?loss\)? (for the (year|period)|after ?tax)'),
           ('eps', r'earnings?\s*per\s*(equity\s*)?share|^basic\b|^eps\b'),
           ('div_total', r'^total dividends?(?!.*(tax|preference))'),
           ('div_interim', r'^((first|second|third|fourth) )?interim dividend(?!.*(tax|preference))'),
           ('div_final', r'^(proposed|final)( final)? dividend(?!.*(tax|preference))|^proposed dividend on equity|'
                         r'^provision for (proposed )?(equity )?dividend(?!.*(tax|preference))'),
           ('div_plain', r'^dividends?\b(?!.*(tax|preference))'),
           ('approp', r'balance (carried|transferred) to (the )?balance sheet|^balance carried forward|^surplus carried')],
    'cf': [('cfo', r'net cash.*operating activit|cash (generated )?(flows? )?(from|used in|generated from) operating activit|'
                   r'cash flows? from/\(used in\) operating activit|^(used|generated|provided)\b.{0,30}operating activit|'
                   r'net cash.*\(a\)$'),
           ('cf_pbt', r'^(net )?(profit|income|earnings)[^a-z]*(loss)?[^a-z]*(for the (year|period))? ?before (income )?tax(es|ation)?\b(?! paid)')],
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
                nums = lambda x: sum(1 for t in tokens(x) if (',' in t[0] or '.' in t[0]) and len(re.sub(r'\D', '', t[0])) >= 3)
                # a real spread has figures on both sides; a page whose labels (left) and figures (right, under the
                # heading) were cut apart is one statement
                if len(re.sub(r'\s', '', left)) > 200 and len(re.sub(r'\s', '', right)) > 200 and nums(left) >= 6 and                         nums(right) >= 6:
                    return [left, right]
    return [t]


def respread(pgs):
    """Saved pages after a change to split_spread: put each 'nL' / 'nR' pair back together and split it again."""
    out, i = [], 0
    while i < len(pgs):
        pid, t = pgs[i]
        if pid.endswith('L') and i + 1 < len(pgs) and pgs[i + 1][0] == pid[:-1] + 'R':
            L, R = t.split(chr(10)), pgs[i + 1][1].split(chr(10))
            w = max(len(x) for x in L)
            t = chr(10).join((L[k].ljust(w) if k < len(L) else ' ' * w) + (R[k] if k < len(R) else '') for k in range(max(len(L), len(R))))
            parts = split_spread(t)
            out += [(pid[:-1], t)] if len(parts) == 1 else [(pid, parts[0]), (pid[:-1] + 'R', parts[1])]
            i += 2
        else:
            out.append((pid, t))
            i += 1
    return out


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


def value_tokens(l, cols):
    """The numbers on a line that sit in one of the page's value columns (or right of the first, when comma/decimal)."""
    strong = lambda t: (',' in t[0] or '.' in t[0]) and len(re.sub(r'\D', '', t[0])) >= 3
    return [t for t in tokens(l) if any(abs(t[2] - c) <= 4 for c in cols) or
            (cols and (strong(t) and t[2] >= min(cols) - 15 or t[0] in '—–-' and t[2] >= min(cols) - 6))]


def split_at(lines, cols):
    """The x that separates the current year from the previous one: with an even number of value columns (one or two
    per year), the middle; otherwise the column gap nearest the middle of the two header years (or Current/Previous),
    unless another gap splits more lines evenly (as many numbers left of it as right: a page with 'Sales' and 'Less:
    excise duty, net' lines puts numbers in two sub-columns per year, and jittered text shifts the header years)."""
    cols = sorted(cols)
    gaps = [(a + b) / 2 for a, b in zip(cols, cols[1:])]
    if not gaps:
        return None
    if len(cols) % 2 == 0:
        return gaps[len(gaps) // 2]
    g0 = None
    for l in lines[:25]:
        ys = [m.end() for m in re.finditer(r'(19|20)\d\d\b', l)]
        cp = re.search(r'current\s+year', l, re.I), re.search(r'previous\s+year', l, re.I)
        h = ys[:2] if len(ys) == 2 and ys[1] - ys[0] > 8 else [cp[0].end(), cp[1].end()] if all(cp) else None
        if h:
            g0 = min(gaps, key=lambda g: abs(g - sum(h) / 2))
            break
    if g0 is None:
        return None
    tk = [value_tokens(l, cols) for l in lines]

    def score(g):
        sc = 0
        for t in tk:
            a = sum(1 for x in t if x[2] <= g)
            b = len(t) - a
            sc += 1 if a == b >= 1 else -1 if a > 1 or b > 1 else 0
        return sc
    best = max(gaps, key=score)
    return best if score(best) > score(g0) else g0


def strip_section(raw):
    """'INCOME        Sales (Gross)': a section heading in capitals standing in the label column before the label."""
    return re.sub(r"^\s*(INCOME|EXPENDITURE|EXPENSES|APPROPRIATIONS?|LIABILITIES|ASSETS|SOURCES OF FUNDS|APPLICATION OF FUNDS|"
                  r"LOAN FUNDS|SHAREHOLDERS['’]? FUNDS|FIXED ASSETS|CURRENT ASSETS[A-Z ,&]*|INVESTMENTS|PROFIT|"
                  r"CAPITAL AND LIABILITIES)\s{4,}(?=[A-Za-z(])", '', raw)


LIG = str.maketrans({'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st', 'ﬆ': 'st'})


def clean_label(label):
    label = re.sub(r'\s+', ' ', label.translate(LIG)).strip().lower()
    label = re.sub(r'(?<![a-z])(?:[a-z] ){2,}[a-z](?![a-z])', lambda m: m.group(0).replace(' ', ''), label)  # 'T O T A L'
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


def left_layout(lines):
    """Pages that print the previous year's figures in a column LEFT of the labels (BANARISUG: '90,224.86  Sales  13  84,287.37'),
    when the column headings confirm it (the earlier year sits left of the later one). Returns (lines rewritten as
    'label  current...  previous', x that splits current from previous), else None."""
    VAL = re.compile(r'\(?-?\d[\d,]*(?:\.\d+)?\)?|--+|[—–]')
    DASH = re.compile(r'--+|[—–]')
    isval = lambda t: DASH.fullmatch(t) or ',' in t or '.' in t or len(re.sub(r'\D', '', t)) >= 3
    rows, rmax, lend = [], 0, 0
    for l in lines:
        fa = re.search(r'[A-Za-z]', l)
        la = max((m.start() for m in re.finditer(r'[A-Za-z]', l)), default=-1)
        if not fa:
            rows.append(None)
            continue
        chunk = l[:fa.start()]
        if re.search(r'\d{1,2}[./-]\d{1,2}[./-](19|20)\d\d|(?<![\d.,])(19|20)\d\d(?![\d.,])', chunk):
            rows.append(None)
            continue
        ms = [m for m in VAL.finditer(chunk) if isval(m.group(0))]
        rt = tokens(l[la + 1:])
        rows.append(([m.group(0) for m in ms], la, fa.start(), rt) if ms else None)
        if ms:
            lend = max(lend, ms[-1].end())
            for t, s_, e_ in rt:
                rmax = max(rmax, la + 1 + e_)
    # the header: the earlier year left of the later one
    yrs = []
    for l in lines[:20]:
        for m in re.finditer(r'\b\d{1,2}[./-]\d{1,2}[./-]((?:19|20)?\d\d)\b|(?<![\d.,])((?:19|20)\d\d)(?![\d.,])', l):
            y_ = int(m.group(1) or m.group(2))
            yrs.append((y_ % 100, m.start()))
    both = [r for r in rows if r and r[0] and r[3]]
    if len(both) < 8 or len({y for y, _ in yrs}) < 2:
        return None
    lo, hi = min(yrs), max(yrs)
    first_lo = min(x for y, x in yrs if y == lo[0])
    last_hi = max(x for y, x in yrs if y == hi[0])
    if not first_lo < last_hi or hi[0] - lo[0] > 1:
        return None
    P = rmax + 22
    out = []
    for l, r in zip(lines, rows):
        if r is None and not re.search(r'[A-Za-z]', l):  # unlabeled subtotal: figure(s) in the left column, then the rest
            tk = tokens(l)
            lt_ = [t for t in tk if t[2] <= lend + 3]
            rt_ = [t for t in tk if t[2] > lend + 3]
            if lt_ and rt_ and isval(lt_[-1][0]):
                prev = '-' if DASH.fullmatch(lt_[-1][0]) else lt_[-1][0]
                new = (' ' * rt_[0][1] + l[rt_[0][1]:]).rstrip()
                out.append(new.ljust(P - len(prev)) + prev)
                continue
        if not r:
            out.append(l)
            continue
        lt, la, fa, rt = r
        label = l[fa:la + 1].strip()
        new = label.ljust(la + 1) + l[la + 1:]
        prev = '-' if DASH.fullmatch(lt[-1]) else lt[-1]
        out.append(new.rstrip().ljust(P - len(prev)) + prev)
    return out, rmax + 11


def parse_page(text, stmt):
    """{field: [current, previous]} in the page's own unit, notes, the year split x, and {field: 'several'} flags."""
    lines = text.splitlines()
    ll = left_layout(lines)
    if ll:
        lines = ll[0]
    cols = columns(lines)
    mid = ll[1] if ll else split_at(lines, cols)
    out, notes, pending, flags, unl = {}, [], '', {}, []
    after_less = False
    # two currencies side by side (Rs and USD per year): the Rs column is the one wanted (the first when Rs is named first)
    usd = False
    for l in lines[:14]:
        m1 = re.search(r'(\bRs\b|`|₹|\bINR\b)', l, re.I)
        m2 = re.search(r'\b(USD|US\s?\$|US\s+dollars?)', l, re.I)
        if m1 and m2:
            usd = m1.start() < m2.start()  # Rs named first: the first number of each year is the Rs one
            break
    seq, multi, pat_c = [], {}, []
    gap = False
    for l in lines:
        if not l.strip():
            gap = True  # a blank line: a wrapped label may continue, but figures without a label do not belong to it
            continue
        tk = value_tokens(l, cols)
        if tk and re.search(r'(19|20)\d\d\s*[-–/]\s*(\d\d|(19|20)\d\d)\b', l) and not any(',' in t[0] or '.' in t[0] for t in tk):
            tk = []  # a '2008-09' column heading, not numbers
        elif tk and re.search(r'\b\d{1,2}[./-]\d{1,2}[./-](19|20)\d\d\b', l) and not any(',' in t[0] for t in tk):
            tk = []  # a '31.03.2007' column heading
        label = clean_label(strip_section(l[:tk[0][1]] if tk else l))
        if 'current liabilities' in label and ('less' in label or 'provisions' in label):
            after_less = True
        if not tk:
            pending = label if label and len(label) < 90 else ''
            gap = False
            continue
        if gap and not label:
            pending = ''
        gap = False
        if not label and (not pending or not any(re.search(rx, pending) for _, rx in F[stmt])):  # unlabeled subtotal: the funds-employed total repeats (sources = application)
            pair = [cur_ for cur_ in ([val(t) for t, s, e in tk if mid is None or e <= mid][-1:] or [None])] + \
                   ([val(t) for t, s, e in tk if mid is not None and e > mid][-1:] or [None])
            unl.append(tuple(pair))
        if not label and pending:  # value line under its label
            label = pending
        elif pending and label and not any(re.search(rx, label) for _, rx in F[stmt]):
            comb = clean_label(pending + ' ' + label)  # a label wrapped over two lines, the figures on the second
            if re.fullmatch(r'dividends?( paid| declared| proposed| for the year)?', pending) and                     re.fullmatch(r'(interim|final|special|one time special)', label):
                comb = clean_label(label + ' dividend')  # 'Dividend' heading, then 'Interim 343' / 'Final 415'
            if any(re.search(rx, comb) for _, rx in F[stmt]):
                label = comb
        pending = ''
        tk_all = tk
        if mid is not None:  # a note / schedule number (1-2 digits) first on a side that has a real figure too is not a value
            big = lambda t: ',' in t[0] or '.' in t[0] or len(re.sub(r'\D', '', t[0])) >= 3
            drop = set()
            for side in ([t for t in tk if t[2] <= mid], [t for t in tk if t[2] > mid]):
                if len(side) >= 2 and re.fullmatch(r'\d{1,2}', side[0][0]) and any(big(t) for t in side[1:]):
                    drop.add(id(side[0]))
            tk = [t for t in tk if id(t) not in drop]
        cur = [val(t) for t, s, e in tk if mid is None or e <= mid]
        prv = [val(t) for t, s, e in tk if mid is not None and e > mid]
        if mid is not None and len(cur) >= 3 and 1 <= len(prv) < len(cur) - 1:
            # a dash just left of the split, last of the left side, with more numbers left than right: it is the right
            # side's first (inner) column
            last = [t for t in tk if t[2] <= mid][-1]
            if last[0] in '—–-' and mid - last[2] <= 6:
                cur, prv = cur[:-1], [0.0] + prv
        if mid is None and len(cur) == 2:
            cur, prv = cur[:1], cur[1:]
        if usd and len(cur) == 2 and len(prv) in (0, 2):
            cur, prv = cur[:1], prv[:1]
        hit = None
        for fld, rx in F[stmt]:
            if re.search(rx, label):
                if fld in ('cl', 'prov') and not after_less:
                    continue
                if fld == 'eps' and 'dilut' in label and 'basic' not in label:
                    continue
                if fld == 'pbt_pre_exc' and re.search(r'operating|interest|depreciation', label):
                    continue
                if fld == 'pat' and re.search(r'computed|per (equity )?share|basis of', label):
                    continue  # an earnings-per-share line that names the profit it is computed on
                hit = fld
                pair = [cur[-1] if cur else None, prv[-1] if prv else None]
                if fld == 'cfo':  # the last such line wins ('before extraordinary items' lines come first)
                    if re.search(r'before|continuing|discontinu', label):
                        break
                    if 'used in' in label and not re.search(r'from|generated|inflow', label):
                        pair = [None if x is None else -x for x in pair]  # 'net cash used in operating activities 1,234'
                    out[fld] = pair
                    break
                if fld == 'pat':
                    pat_c.append((label, pair, len(cur) > 1 or len(prv) > 1))
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
                        multi[fld] = (cur, prv)
                break
        seq.append((label, cur, prv, hit))
    if stmt == 'pl' and 'pbt' in out and 'pat' in out and len(seq) >= 12:
        # a complete P&L with no mention of interest / depreciation / per-share figures anywhere on the page: the company
        # does not report that item separately (nothing for a helper to find)
        for fld_, rx_ in (('interest', r'interest|financ\w* (cost|charge|expense)|borrowing cost|bank (charge|commission)'),
                          ('dep', r'deprec|amorti[sz]'), ('eps', r'per\s+(equity\s+)?share|\beps\b|earnings?\s+per')):
            if fld_ not in out and not re.search(rx_, text, re.I):
                out['abs_' + fld_] = [1.0, 1.0]
    if stmt == 'pl' and not any(k in out for k in ('div_interim', 'div_final', 'div_plain', 'div_total')) and             re.search(r'(?i)dividend(?!\s*(income|received|from|on (investment|mutual)))', text):
        out['div_seen'] = [1.0, 1.0]  # a dividend is mentioned but no line was read: not the same as none
    if stmt == 'bs' and 'total' not in out:
        rep_ = [p for p, n in collections.Counter(unl).items() if n >= 2 and p[0] is not None]
        if rep_:
            out['total'] = list(max(rep_, key=lambda p: abs(p[0])))
            notes.append('total: repeated unlabeled line (sources = application of funds)')
    if stmt == 'bs':
        # 'Secured loans 170,668 / Unsecured loans 30,000 200,668': the second line carries the subtotal in an outer column
        close = lambda a, b: abs(a - b) <= (2.0 if a == int(a) and b == int(b) else 0.05) + 1e-6 * max(abs(a), abs(b))
        for a_, b_ in (('secured', 'unsecured'), ('unsecured', 'secured'), ('lt_borr', 'st_borr'), ('st_borr', 'lt_borr')):
            if flags.get(b_) == 'several' and a_ in out and b_ in multi and None not in out[a_]:
                (c_, p_) = multi[b_]
                if len(c_) == 2 and len(p_) == 2 and close(out[a_][0] + c_[0], c_[1]) and close(out[a_][1] + p_[0], p_[1]):
                    out[b_] = [c_[0], p_[0]]
                    flags.pop(b_)
        # 'Reserves & surplus 20,564 21,575': the outer figure is share capital + reserves (shareholders' funds)
        if flags.get('reserves') == 'several' and 'reserves' in multi and out.get('share_capital') and                 None not in out['share_capital']:
            (c_, p_) = multi['reserves']
            if len(c_) == 2 and len(p_) == 2 and close(c_[0] + out['share_capital'][0], c_[1]) and                     close(p_[0] + out['share_capital'][1], p_[1]):
                out['reserves'] = [c_[0], p_[0]]
                flags.pop('reserves')
    if stmt == 'pl':
        # sums are checked to the rounding of the figures (whole numbers: a unit or two; two decimals: a few hundredths)
        close = lambda a, b: abs(a - b) <= (2.0 if a == int(a) and b == int(b) else 0.05) + 1e-6 * max(abs(a), abs(b))
        # 'Sales 2,073.68 / Less: excise duty 119.84 1,953.84': two numbers on the excise line, the last the net sales
        if flags.get('excise') == 'several' and 'gross_sales' in out and 'excise' in multi:
            (c_, p_) = multi['excise']
            g_ = out['gross_sales']
            if len(c_) == 2 and len(p_) == 2 and None not in g_ and close(g_[0] - c_[0], c_[1]) and close(g_[1] - p_[0], p_[1]):
                out.setdefault('net_sales', [c_[1], p_[1]])
                out['excise'] = [c_[0], p_[0]]
                flags.pop('excise')
        # unusual sales label ('Earnings from sale of electricity', 'Revenues'): the lines above 'Other income' that add up,
        # with it, to the total line under it
        if not any(k in out for k in ('net_ops', 'net_sales', 'gross_sales', 'int_earned')):
            ix = next((i for i, e in enumerate(seq) if e[3] == 'other_income'), None)
            if ix and ix + 1 < len(seq):
                yr = lambda v: v is not None and v == int(v) and 1990 <= v <= 2100
                pre = [e for e in seq[:ix] if len(e[1]) == 1 and len(e[2]) == 1 and None not in (e[1][0], e[2][0]) and
                       not (yr(e[1][0]) and yr(e[2][0]))]  # a column heading read as numbers is not an income line
                nl, nx = seq[ix + 1][0], seq[ix + 1]
                if pre and all(len(e[1]) == 1 and len(e[2]) == 1 and None not in (e[1][0], e[2][0]) for e in (seq[ix], nx))                         and (not nl or nl.startswith('total')):
                    sc, sp = sum(e[1][0] for e in pre), sum(e[2][0] for e in pre)
                    if close(sc + seq[ix][1][0], nx[1][0]) and close(sp + seq[ix][2][0], nx[2][0]) and sc > 0:
                        out['sum_income'] = [sc, sp]
        # the face of the P&L foots: income total - expenses total = profit before tax (both years); the expenses total is
        # a 'Total expenses' line or an unlabeled line that adds up the expense lines above it
        ix = next((i for i, e in enumerate(seq) if e[3] == 'other_income'), None)
        ti_i = next((i for i, e in enumerate(seq) if e[3] == 'total_income'), None)
        if ti_i is None and ix is not None and ix + 1 < len(seq) and (not seq[ix + 1][0] or seq[ix + 1][0].startswith('total')):
            ti_i = ix + 1
        pb_i = next((i for i, e in enumerate(seq) if e[3] == 'pbt'), None)
        one = lambda e: len(e[1]) == 1 and len(e[2]) == 1 and None not in (e[1][0], e[2][0])
        if ti_i is not None and pb_i is not None and pb_i > ti_i + 1 and 'pbt' in out and None not in out['pbt'] and one(seq[ti_i]):
            ti = seq[ti_i]
            acc = [0.0, 0.0]
            for e in seq[ti_i + 1:pb_i]:
                if len(e[1]) > 1 or len(e[2]) > 1 or not (e[1] or e[2]) or None in e[1] + e[2]:
                    break
                v_ = (e[1][0] if e[1] else 0.0, e[2][0] if e[2] else 0.0)  # a blank column is a nil
                if (e[3] == 'total_exp' or not e[0] or e[0].startswith('total')) and acc[0] and                         close(acc[0], v_[0]) and close(acc[1], v_[1]):
                    k_ = seq.index(e)  # the difference is the profit before tax, or a profit line between the total and it
                    if any(close(ti[1][0] - v_[0], f[1][0]) and close(ti[2][0] - v_[1], f[2][0])
                           for f in seq[k_ + 1:pb_i + 1] if one(f)):
                        out['foot'] = [1.0, 1.0]
                    break
                acc = [acc[0] + v_[0], acc[1] + v_[1]]
        # several profit lines: 'Profit for the year' (often before tax) first, then 'Profit after tax': the last one that
        # names tax is the profit after tax
        if any('discontinu' in c[0] for c in pat_c):  # continuing + discontinued operations: only the '(A+B)' total will do
            cs = [c for c in pat_c if 'continuing' not in c[0]]
            if cs:
                out['pat'] = cs[-1][1]
                pat_c = cs
            else:
                flags['pat'] = 'several'
        at = [c for c in pat_c if re.search(r'after tax', c[0]) and not re.search(r'before|minority', c[0])]
        if at and pat_c and 'after tax' not in pat_c[0][0] and at[-1][1] != out.get('pat'):
            out['pat'] = at[-1][1]
            if at[-1][2]:
                flags['pat'] = 'several'
            else:
                flags.pop('pat', None)
            pat_c = [at[-1]] if len(pat_c) < 2 else pat_c
        # 'Profit for the year' above the tax lines and 'Profit after tax' below them: before-tax profit, then profit
        if 'pbt' not in out and len(pat_c) >= 2 and 'tax' in pat_c[-1][0] and 'tax' not in pat_c[0][0] and all(None not in c[1] for c in pat_c[:1] + pat_c[-1:]):
            p1, p2 = pat_c[0][1], pat_c[-1][1]
            tx = [e for e in seq if 'exceptional' not in e[0] and len(e[1]) == 1 and len(e[2]) == 1 and e[1][0] is not None and e[2][0] is not None and
                  close(abs(e[1][0]), abs(p1[0] - p2[0])) and close(abs(e[2][0]), abs(p1[1] - p2[1]))]
            if tx and p1 != p2:
                out['pbt'], out['pat'] = p1, p2
                out['tax_total'] = [p1[0] - p2[0], p1[1] - p2[1]]
    flags['_ncols'] = len(cols)
    return out, notes, mid, flags


def content_pages(pgs, stmt):
    """Indexes of pages that look like the statement by content, whatever their heading (or lack of one): a balance sheet
    has share capital, reserves, fixed assets and current assets / liabilities with many figures (and is not a schedule
    'as per last balance sheet'); a P&L has income, depreciation and profit lines with many figures."""
    out = []
    for i, (_, t) in enumerate(pgs):
        tl = t.lower()
        n = sum(1 for l in t.splitlines() for x in tokens(l) if ',' in x[0] or '.' in x[0])
        if stmt == 'bs' and n >= 15 and re.search(r'share capital|^\s*capital', tl, re.M) and 'reserves' in tl and 'total' in tl \
                and re.search(r'assets|debtors|receivables', tl) and 'as per last balance sheet' not in tl:
            out.append(i)
        elif stmt == 'pl' and n >= 20 and re.search(r'other income|total income|total revenue|revenue from operations|\bsales\b', tl) \
                and 'depreciation' in tl and re.search(r'before (tax|taxation)', tl) and 'as per last balance sheet' not in tl:
            out.append(i)
    return out


def keep_pages(pgs):
    """The pages to save for one report: every page that opens with a statement heading (strict, then loose when a
    statement has none), pages that look like a statement by content, cash flow pages (operating + investing activities),
    each with the page after it; notes holding the proposed dividend; the whole text when nothing is recognised."""
    hit = stmt_pages(pgs)
    keep = set()
    for i in hit:
        keep |= {i, i + 1} if i + 1 < len(pgs) else {i}
    for stmt in ('bs', 'pl'):
        for i in content_pages(pgs, stmt):
            keep |= {i, i + 1} if i + 1 < len(pgs) else {i}
    for i, (_, t) in enumerate(pgs):
        if re.search(r'operating\s+activit', t, re.I) and re.search(r'investing\s+activit', t, re.I):
            keep |= {i, i + 1} if i + 1 < len(pgs) else {i}
    if not keep:  # no statement heading recognised: keep the whole text so a helper can find the statements
        keep = set(range(len(pgs)))
    dpg = [i for i, (_, t) in enumerate(pgs) if re.search(r'(?im)^\s*(proposed|final|interim)\s+(final\s+)?(equity\s+)?'
                                                       r'dividends?\b(?!.*(tax|per share|preference)).*\d', t)]
    return keep | set(dpg[:8])  # notes holding the proposed dividend (new format)


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


def entity(t):
    """The company name at the top of a statement page (a short line with Limited / Ltd / FZE ... that is not a heading),
    lower-cased without the legal suffix; None when the page names none."""
    for l in [x.strip() for x in t.splitlines() if x.strip()][:6]:
        if re.search(r'(?i)formerly|erstwhile|known as|previously|now called', l):
            continue
        l = re.split(r'(?i)[-–—]\s*(?=consolidated|standalone|financial|annual|statement)', l)[0].strip()  # 'X LTD.- CONSOLIDATED ...'
        if len(l) < 70 and re.search(r'(?i)\b(limited|ltd\.?|fze|inc\.?|llc|pte|plc|corporation|corp\.?|gmbh)\b', l) and \
                not re.search(r'(?i)statement|balance|profit|cash ?flow|schedule|notes|auditor|report|annexure', l):
            return norm_name(l)
    return None


def norm_name(l):
    n = re.sub(r'\b(limited|ltd|private|pvt|the|company|co|corporation|corp|and|its|subsidiar(y|ies)|group|consolidated)\b', ' ',
               re.sub(r'[^a-z ]', ' ', l.lower().replace('&', ' and ')))
    return re.sub(r'\s+', ' ', n).strip() or None


def name_ratio(ent, cname):
    """How well a page's entity matches the company's names (None when either is unknown)."""
    import difflib
    if not ent or not cname:
        return None
    return max(difflib.SequenceMatcher(None, ent, c).ratio() for c in cname if c)


def same_entity(a, b):
    import difflib
    return not a or not b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def find(pgs, stmt, anchors=None, cname=None):
    """find_one() with the strict headings; for a basis it found nothing for, the looser headings ('Consolidated Balance
    Sheet' with the date on the next line, 'Profit and Loss Statement')."""
    best = find_one(pgs, stmt, anchors, cname)
    if stmt in HEAD_LOOSE:
        strict = HEAD[stmt]
        HEAD[stmt] = HEAD_LOOSE[stmt]
        try:
            for b_, v in find_one(pgs, stmt, anchors, cname).items():
                best.setdefault(b_, v)
        finally:
            HEAD[stmt] = strict
        for b_, v in find_one(pgs, stmt, anchors, cname, True).items():  # by content, for a basis still without a page
            best.setdefault(b_, v)
    return best


def find_one(pgs, stmt, anchors=None, cname=None, content=False):
    """Statement pages by heading, best-scoring page per basis -> {basis: (score, page id, fields, notes, mid, flags)}.
    pgs = [(id, text)]; pages that open with the heading are preferred over pages that merely name it. anchors =
    {basis: (PDF page number, company name) of that basis's P&L / balance sheet}: a cash flow page more than 150 pages
    from it, or headed by a different company (a subsidiary's accounts in the same report), is ignored; nearer ones win ties."""
    best = {}
    idx = [i for i, (_, t) in enumerate(pgs) if stmt_head(t, stmt)]
    if not idx:
        idx = [i for i, (_, t) in enumerate(pgs) if re.search(HEAD[stmt], ' '.join(t[:2500].split()).upper())]
    if content:
        idx = content_pages(pgs, stmt)
    if stmt == 'cf':
        # a cash flow page is one with operating and investing activities on it; the heading is often missing (title on the
        # page before) and a heading hit may be the auditors' report that names the statement
        body = lambda t: re.search(r'operating\s+activit', t, re.I) and re.search(r'investing\s+activit', t, re.I)
        idx = sorted(set(idx) | {i for i, (_, t) in enumerate(pgs) if body(t)})
    if cname and idx:  # a subsidiary's statements printed in the same report: keep the pages of the company itself
        rat = {i: name_ratio(entity(pgs[i][1]), cname) for i in idx}
        mx = max([r_ for r_ in rat.values() if r_ is not None] or [0])
        if mx >= 0.95:  # a subsidiary's name is mostly well under 0.85 of the company's (a garbled own name stays)
            idx = [i for i in idx if rat[i] is None or rat[i] >= 0.85]
    for i in idx:
        pid, p = pgs[i]
        head = ' '.join(p[:2500].split()).upper()
        m = re.search(HEAD[stmt], head)
        if content and not m:
            basis = 'consolidated' if 'CONSOLIDATED' in head[:600] else 'standalone'
        elif m:
            basis = 'consolidated' if 'CONSOLIDATED' in head[max(0, m.start() - 200):m.end() + 100] or                 'CONSOLIDATED' in head[:300] else 'standalone'
        else:
            # no heading on the page: the basis of the statement page just before it (the page before, or two before, by
            # PDF page number); a headingless cash flow page far from the statements may be a subsidiary's, so it is skipped
            basis = None
            num = lambda x: int(re.match(r'\d+', x).group()) if re.match(r'\d+', x) else None
            for j in range(i - 1, max(-1, i - 3), -1):
                hs = ' '.join(pgs[j][1][:2500].split()).upper()
                ms = [re.search(HEAD[x], hs) for x in HEAD if stmt_head(pgs[j][1], x)]
                if ms and num(pgs[i][0]) is not None and num(pgs[j][0]) is not None and 0 <= num(pgs[i][0]) - num(pgs[j][0]) <= 2:
                    mm = ms[0]
                    basis = 'consolidated' if 'CONSOLIDATED' in hs[max(0, mm.start() - 200):mm.end() + 100] or                         'CONSOLIDATED' in hs[:300] else 'standalone'
                    break
            if basis is None:
                continue
        o, n, mid, fl = parse_page(p, stmt)
        if stmt == 'bs' and len(o) < 4 and i + 1 < len(pgs):  # statement split over two pages
            o2, n2, _, fl2 = parse_page(pgs[i + 1][1], stmt)
            o = {**o2, **o}
            fl = {**fl2, **fl}
        if stmt == 'cf' and 'cfo' not in o:
            continue
        score = len([k for k in o if k not in ('foot', 'sum_income', 'total_exp', 'div_seen') and not k.startswith('abs_')]) + (3 if mid else 0) +             (5 if stmt == 'cf' and 'cfo' in o else 0) + (2 if stmt == 'cf' and re.search(r'investing\s+activit', p, re.I) else 0)
        if stmt == 'cf' and anchors is not None:
            pn = re.match(r'\d+', pid)
            a_ = anchors.get(basis)
            if a_ is None or not pn or abs(int(pn.group()) - a_[0]) > 150 or not same_entity(entity(p), a_[1]):
                continue
            score -= abs(int(pn.group()) - a_[0]) / 1000
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


def paise_like(text):
    """True when most of a page's figures are small numbers with decimals (1,234.56): they cannot be whole rupees."""
    big = [t for l in text.splitlines() for t in tokens(l) if re.search(r'\.\d\d$', t[0].rstrip(')'))]
    ints = [t for l in text.splitlines() for t in tokens(l) if '.' not in t[0] and len(re.sub(r'\D', '', t[0])) >= 5]
    small = [t for t in big if float(re.sub(r'[^\d.]', '', t[0]) or 0) < 1e5]
    return len(small) >= 8 and len(small) > 2 * len(ints)


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
        if s is None and g(pl, 'turnover', j) is not None and g(pl, 'gross_sales', j) is not None:
            s, sk = g(pl, 'turnover', j), 'turnover'  # 'Gross turnover ... Turnover': the plain line is the net
        if s is None and g(pl, 'gross_sales', j) is not None:
            s, sk = g(pl, 'gross_sales', j) - (g(pl, 'excise', j) or 0), 'gross_sales'
        if s is None and g(pl, 'turnover', j) is not None:
            s, sk = g(pl, 'turnover', j), 'turnover'
        if s is None and g(pl, 'sum_income', j) is not None:
            s, sk = g(pl, 'sum_income', j), 'sum_income'
        put('sales', g(pl, 'int_earned', j) if bank else s, 'pl', conf('pl', 'int_earned' if bank else sk))
        for k in ('interest', 'dep', 'pbt', 'tax', 'pat'):
            put(k, g(pl, k, j), 'pl')
        if 'pbt' not in r and g(pl, 'pbt_pre_exc', j) is not None and not g(pl, 'exceptional', j):
            put('pbt', g(pl, 'pbt_pre_exc', j), 'pl')  # 'Profit before tax and exceptional items' with no exceptional item
        dv = [g(pl, k, j) for k in ('div_interim', 'div_final')]
        if g(pl, 'div_total', j) is not None:
            put('dividend', abs(g(pl, 'div_total', j)), 'pl')  # a 'Total dividend' line (interim + final + special)
        elif any(x is not None for x in dv):
            put('dividend', abs(sum(x for x in dv if x is not None)), 'pl')
            if pages.get('div_page'):
                r['dividend'][1:] = ['medium', pages['div_page']]
        elif g(pl, 'div_plain', j) is not None:
            put('dividend', abs(g(pl, 'div_plain', j)), 'pl')
        elif pl.get('approp') is not None and pl.get('div_seen') is None:
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
        if pl.get('foot'):
            r['_foot'] = [1.0, 'high', None]
        for f_ in ('interest', 'dep', 'eps'):
            if pl.get('abs_' + f_) and f_ not in r:
                r['_abs_' + f_] = [1.0, 'high', None]
        ti_ = g(pl, 'total_income', j)  # sales + other income = the total income line: the sales line is the right one
        if not bank and ti_ and s is not None and abs(s + (oi or 0) - ti_) <= 0.015 * abs(ti_):
            r['_sales_ok'] = [1.0, 'high', None]
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
        if bank and ('pbt' not in r or r['pbt'][1] == 'low') and g(cf, 'cf_pbt', j) is not None and 'pat' in r and                 r['pat'][1] != 'low':
            # banks print the tax inside 'Provisions and contingencies'; the cash flow statement starts from 'Net profit
            # before taxes', so tax = that - net profit (taken when it is a plausible share of it)
            pb = g(cf, 'cf_pbt', j)
            tx = pb - r['pat'][0]
            if pb > 0 and 0 <= tx <= 0.6 * pb:
                put('pbt', pb, 'cf', 'medium')
                put('tax', tx, 'cf', 'medium')
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
            put('borrowings', sum(p for p in parts if p is not None), 'bs',
                'low' if any(flags.get('bs', {}).get(k) == 'several' for k in
                             ('secured', 'unsecured', 'lt_borr', 'st_borr', 'borr', 'deposits')) else None)
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


def checks(r, foot=False):
    """Internal consistency: False = fails (the fields go to a helper). foot: the P&L's own totals add up to the profit
    before tax, so a very high or low margin is the company's, not a misread."""
    v = lambda k: r[k][0] if k in r else None
    c = {}
    if None not in (v('pbt'), v('tax'), v('pat')):
        c['pbt-tax=pat'] = abs(v('pbt') - abs(v('tax')) - v('pat')) <= max(0.5, 0.03 * abs(v('pat'))) or \
            abs(v('pbt') - v('tax') - v('pat')) <= max(0.5, 0.03 * abs(v('pat')))
    if v('op') is not None and v('sales'):
        c['opm_plausible'] = True if foot else -100 < v('op') / v('sales') * 100 < 80
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


def parse_pages(pgs, fy_hint=None, fym=3, cname=None):
    """pgs: list of (page_no, text). -> result dict (bases with years, fields, checks, helper lists). cname: the company's
    names (list), to tell its statements from a subsidiary's printed in the same report."""
    pgs = [(i, t.translate(LIG)) for i, t in pgs]
    found = {s: find(pgs, s, None, cname) for s in ('bs', 'pl')}
    anc = {}
    for b_ in ('standalone', 'consolidated'):
        ps = [(re.match(r'\d+', found[s][b_][1]), found[s][b_][1]) for s in ('pl', 'bs') if b_ in found[s]]
        ps = [x for x in ps if x[0]]
        anc[b_] = (int(ps[0][0].group()), next((entity(t) for pid, t in pgs if pid == ps[0][1]), None)) if ps else None
    found['cf'] = find(pgs, 'cf', anc, cname)
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
                if units[s][0] == 1e-7 and paise_like(text_of[pick[s][1]]):
                    units[s] = (None, '')  # 'Rupees' heading over figures with decimals: not whole rupees
        known = [u for u in units.values() if u[0] is not None]
        for s in units:
            if units[s][0] is None and known:  # a page without a unit word: the basis's other pages' unit
                units[s] = (known[0][0], known[0][1] + ' (from another statement page)')
        unit = all(u[0] is not None for u in units.values()) or None
        uword = {s: u[1] for s, u in units.items()}
        d = {s: ({k: ([None if x is None else x * units[s][0] for x in v] if k not in ('eps', 'foot') else v)
                  for k, v in pick[s][2].items()}
                 if pick[s] and units[s][0] is not None else (pick[s][2] if pick[s] else {})) for s in pick}
        flags = {s: (pick[s][5] if pick[s] else {}) for s in pick}
        pages = {s: pick[s][1] if pick[s] else None for s in pick}
        pages.update({s + '_split': bool(pick[s] and pick[s][4]) for s in pick})
        if pages['bs']:
            bt = text_of[pages['bs']].lower()
            pages['bs_noloans'] = not re.search(r'borrowing|secured|loan funds|\bloans?\b(?! and advances| & advances)|'
                                                r'debenture|deposits', bt)
        if pages['pl'] and not any(k in d['pl'] for k in ('div_interim', 'div_final', 'div_plain', 'div_total', 'approp')):
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
        if len(yrs) == 2 and not yrs[1] and all((pick[x][5] or {}).get('_ncols', 2) <= 1 for x in ('bs', 'pl') if pick[x]):
            yrs = yrs[:1]  # the company's first year: one value column, no previous year in this report
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
        B['unit_missing'] = not unit
        for j, y in enumerate(yrs):
            foot = y.pop('_foot', None) is not None
            sok = y.pop('_sales_ok', None) is not None
            absent = {k_[5:] for k_ in list(y) if k_.startswith('_abs_')}
            for k_ in absent:
                y.pop('_abs_' + k_)
            ck, helper = finish_year(y, bank, foot, bool(out.get('note_year')), absent)
            key = f'{(yend.year - j) if yend else "?"}-{yend.month:02d}' if yend else f'cur-{j}'
            B['years'][key] = {'fields': {k: [round(x[0], 4), x[1], x[2]] for k, x in y.items()}, 'checks': ck,
                               'helper': helper, 'foot': foot, 'sales_ok': sok, 'absent': sorted(absent)}
        out['bases'][basis] = B
    # the directors' report says no dividend was recommended (current year only; not when an interim dividend is mentioned)
    alltext = ' '.join(' '.join(t.split()) for _, t in pgs)
    if re.search(r"(?i)(do not|does not|did not|have not|has not|are unable to|is unable to|unable to|not)\s+(recommend|recommended|declare|declared|propose|proposed)\s+(to\s+)?(any\s+|a\s+)?(final\s+)?dividend|no\s+dividend\s+(is|was|has been|have been)\s+(recommended|proposed|declared)", alltext) \
            and not re.search(r'(?i)interim dividend', alltext):
        for B_ in out['bases'].values():
            k_ = next(iter(B_['years']), None)
            y_ = B_['years'].get(k_) if k_ else None
            if y_ and 'dividend' not in y_['fields'] or (y_ and y_['fields']['dividend'][1] == 'low'):
                y_['fields']['dividend'] = [0.0, 'medium', 'directors report: no dividend recommended']
                y_['helper'] = [f for f in y_['helper'] if f != 'dividend']
    # the dividend is the company's (the parent's), the same on either basis: a consolidated year without a dividend line
    # takes the standalone year's from the same report
    sa, co = out['bases'].get('standalone'), out['bases'].get('consolidated')
    if sa and co:
        for k, y in co['years'].items():
            sy = sa['years'].get(k)
            if sy and 'dividend' in sy['fields'] and sy['fields']['dividend'][1] != 'low' and 'dividend' not in sy['helper'] and \
                    ('dividend' not in y['fields'] or 'dividend' in y['helper'] or y['fields']['dividend'][1] == 'low'):
                y['fields']['dividend'] = [sy['fields']['dividend'][0], 'medium', 'standalone ' + str(sy['fields']['dividend'][2])]
                y['helper'] = [f for f in y['helper'] if f != 'dividend']
    return out


def finish_year(y, bank, foot, note_year, absent=()):
    """(checks, helper fields) of one year's {field: [value, confidence, page]}."""
    ck = checks(y, foot)
    need = NEED_BANK if bank else NEED
    helper = ({f for f in need if f not in y or y[f][1] == 'low'} - set(absent)) | \
        {f for k, ok in ck.items() if ok is False for f in CHECK_FIELDS[k] if f in need}
    if isinstance(ck.get('magnitude'), list):
        helper |= {f for f in ck['magnitude'] if f in need}
        if set(ck['magnitude']) - {'cfo'}:
            helper |= {'sales', 'total_assets'}
        ck['magnitude'] = False
    if len(helper) > len(need) / 2:  # mostly unread: the rest of this column isn't trusted either
        helper = set(need)
    if note_year:
        helper.add('year_end')
    return ck, sorted(helper)


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


def company_names(sym):
    """The company's names today (screener, BSE), as norm_name() makes them: to tell its statements from a subsidiary's."""
    raw = []
    ov = ((load(os.path.join(COMP, sym, 'scr', 'overview.json')) or {}).get('data') or {})
    if ov.get('name'):
        raw.append(ov['name'])
    p = os.path.join('data', 'market', 'bse_codes.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r['nse_symbol'] == sym and r.get('bse_name'):
                raw.append(r['bse_name'])
    return [n for n in dict.fromkeys(norm_name(re.sub(r'\(.*?\)', '', x)) for x in raw) if n]


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


def rescale_basis(res, b, fac):
    """Figures read raw (no unit on the statements) are in a unit that is 1/fac of a crore: divide every amount."""
    B = res['bases'][b]
    for k, y in B['years'].items():
        for f, v in y['fields'].items():
            if f != 'eps':
                v[0] = round(v[0] / fac, 4)
            if v[1] == 'low':
                v[1] = 'medium'
        if y.get('chart_sales_ratio'):
            y['chart_sales_ratio'] = round(y['chart_sales_ratio'] / fac, 3)
        yy = {f: list(v) for f, v in y['fields'].items()}
        y['checks'], y['helper'] = finish_year(yy, B['bank'], y.get('foot'), bool(res.get('note_year')), y.get('absent') or ())
    B['unit_missing'] = False
    B['unit_from_chart'] = fac
    B['notes'] = [n for n in B['notes'] if n != 'unit not found'] + [f'no unit on the statements: figures are in 1/{fac:g} crore (sales within 33% of the chart)']


def chart_check(sym, res, cache={}):
    """Sales against the chart's TTM sales 75 days after the year end (history.json, from 2005). Statements without any
    unit word: when every year's sales/chart ratio lies within 33% of one standard unit (rupees 1e7, lakhs 100, millions
    10, thousands 1e4), that is the unit. Otherwise when no basis is within 25% of the chart, that year's sales go to a
    helper, unless the P&L's total income line confirms the sales line (sales + other income = total income: then the
    chart is on another basis or restated; the ratio stays in the file); a ratio near 10, 100, 1000 (or their inverse)
    means a wrong unit, so every field of that basis-year goes."""
    import mb_features as mf
    if sym not in cache:
        cache.clear()
        cache[sym] = mf.Company(sym, COMP, chart_only=True)
    c = cache[sym]
    keys = {k for B in res.get('bases', {}).values() for k in B['years'] if re.match(r'\d{4}-\d\d$', k)}
    def ratios():
        for k in keys:
            e = mf.month_end(int(k[:4]), int(k[5:]))
            cv = c.sales.lookup(e + dt.timedelta(days=75)) if c.sales.raw else None
            if not cv or cv <= 0:
                continue
            for b, B in res['bases'].items():
                y = B['years'].get(k)
                if y and 'sales' in y['fields'] and y['fields']['sales'][0]:
                    y['chart_sales_ratio'] = round(y['fields']['sales'][0] / cv, 3)
    ratios()
    for b, B in list(res['bases'].items()):
        if B.get('unit_missing'):
            xs = [y['chart_sales_ratio'] for y in B['years'].values() if y.get('chart_sales_ratio')]
            fits = [fac for fac in (1.0, 1e7, 1e2, 10, 1e4) if xs and all(0.75 * fac <= x <= 1.33 * fac for x in xs)]
            if len(fits) == 1:
                rescale_basis(res, b, fits[0])
    for k in sorted(keys):
        rs = {b: B['years'][k]['chart_sales_ratio'] for b, B in res['bases'].items()
              if k in B['years'] and B['years'][k].get('chart_sales_ratio') is not None}
        if not rs or any(0.75 <= x <= 1.33 for x in rs.values()):
            continue
        for b, x in rs.items():
            y = res['bases'][b]['years'][k]
            unitlike = any(abs(x * 10 ** n - 1) < 0.15 for n in range(-7, 8) if n)
            if not unitlike and y.get('sales_ok'):
                continue
            add = [f for f in (NEED_BANK if res['bases'][b]['bank'] else NEED)] if unitlike else ['sales']
            y['helper'] = sorted(set(y['helper']) | set(add))
            y['checks']['chart_sales'] = False
            res['bases'][b]['notes'].append(f'{k} sales {x:.2f}x the chart TTM sales' + (' (unit?)' if unitlike else ''))
    return res


def save_report(sym, pgs, keep, url, src, ry, fym):
    """Save the statement pages and parsed JSON; returns (result dict, json path, pages path)."""
    sel = [pgs[i] for i in sorted(keep)]
    res = chart_check(sym, parse_pages(sel, ry, fym, company_names(sym)))
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
    w = csv.DictWriter(open(p, 'w', newline='', encoding='utf-8'), fieldnames=['sym', 'fy', 'fym', 'code', 'scr_first', 'rows'])
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
            keep = keep_pages(pgs)
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
            pgs = respread(read_pages_file(r['pages_file']))
            res = chart_check(r['sym'], parse_pages(pgs, int(r['report_fy']), int(r['fym'] or 3), company_names(r['sym'])))
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


def refetch(a):
    """Download again (recorded url, default gap) the reports whose saved pages lack a balance sheet, P&L or cash flow
    for some basis (or any statement), and save the pages with the current page selection (keep_pages)."""
    D = hist_dir()
    rows = read_status(D)
    only = set(a.syms.split(',')) if a.syms else None
    plan_need = collections.defaultdict(set)
    for r in csv.DictReader(open(os.path.join(D, 'ar_plan.csv'), encoding='utf-8')):
        plan_need[r['sym']].add(int(r['fy']))
    todo = []
    for r in rows:
        if r['result'] != 'needs-helper' or not r['url'] or not r['json_file'] or (only and r['sym'] not in only):
            continue
        res = load(r['json_file']) or {}
        if res.get('refetched'):
            continue
        if not res.get('bases') or any(not B['pages'].get(x) for B in res['bases'].values() for x in ('bs', 'pl', 'cf')):
            todo.append(r)
    print('reports to download again:', len(todo))
    if a.dry:
        for r in todo:
            print(r['sym'], r['report_fy'], r['url'])
        return
    tmp = a.tmp or tempfile.gettempdir()
    os.makedirs(tmp, exist_ok=True)
    t0 = time.time()
    for k, r in enumerate(todo):
        d = tempfile.mkdtemp(prefix=f'ar_{r["sym"]}_re_', dir=tmp)
        try:
            f = curl_get(r['url'], os.path.join(d, 'r.bin'))
            time.sleep(a.gap)
            if not f:
                r['note'] = (r['note'] + '; ' if r['note'] else '') + 'refetch: download failed'
                continue
            pgs = pdf_pages(f)
            keep = keep_pages(pgs)
            ry = int(r['report_fy'])
            res, jf, pf = save_report(r['sym'], pgs, keep, r['url'], r['src'], ry, int(r['fym'] or 3))
            res['refetched'] = dt.date.today().isoformat()
            json.dump(res, open(jf, 'w', encoding='utf-8'), indent=1)
            for old, new in ((r['json_file'], jf), (r['pages_file'], pf)):
                if old and old.replace(chr(92), '/') != new.replace(chr(92), '/') and os.path.exists(old):
                    os.remove(old)
            result, note = result_of(res)
            r.update(result=result, years=' '.join(sorted({y for b in res['bases'].values() for y in b['years']})),
                     bases=' '.join(res['bases']), helper_fields=helper_summary(res, plan_need[r['sym']]),
                     pages_file=pf.replace(chr(92), '/'), json_file=jf.replace(chr(92), '/'), mb=round(os.path.getsize(f) / 1e6, 1),
                     note='; '.join(x for x in (note, res.get('note_link_year', ''), res.get('note_year', '')) if x))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        if k % 10 == 0:
            print(f'{k + 1}/{len(todo)} reports, {time.time() - t0:.0f}s', flush=True)
    with open(os.path.join(D, 'ar_status.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=STATUS_COLS)
        w.writeheader()
        w.writerows(rows)
    print('done', len(todo), 'reports', f'{time.time() - t0:.0f}s')


# ------------------------------------------------------------------ queue ---------------------------------------------------
def cross_check(sym):
    """Across one company's reports: the same year read from two reports (current column of its own report, previous
    column of the next), and consecutive years, are compared on sales, PAT, total assets, reserves and equity capital.
    A wrong unit moves every amount by the same power of ten; one field alone off by a power of ten is a misread
    field, or (consecutive years) real growth. So: two or more fields off by the same power of ten = unit error, the
    whole basis-year of both reports goes to a helper, unless one of the two reports printed no unit (its figures are
    raw rupees, lakhs ...) and the gap is a standard unit: then that basis is rescaled; one field off by a power of ten
    while others agree, in two reports of the same year = that field goes to a helper in both; one comparable field
    only: same year = whole basis-year, consecutive years = only a 100-fold or more change in sales / total assets
    counts. Flags are written into the reports' JSON (checks.cross_unit, checks.cross_field). Returns the number of
    basis-years flagged."""
    FS = ('sales', 'pat', 'total_assets', 'reserves', 'equity_cap')
    reps = {}
    for jf in glob.glob(os.path.join(COMP, sym, 'FY*Q4', 'ar_FY*.json')):
        if not jf.endswith('_helper.json'):
            reps[jf] = load(jf) or {}
    vals = collections.defaultdict(list)  # (basis, year key) -> [(jf, field values)]
    for jf, r in reps.items():
        for b, B in (r.get('bases') or {}).items():
            for k, y in B['years'].items():
                if re.match(r'\d{4}-\d\d$', k):
                    vals[(b, k)].append((jf, {f: v[0] for f, v in y['fields'].items()}))

    def pw(q):  # n when q is within 20% of 10^n (n != 0); 0 when q is within 25% of 1
        if 0.8 <= q <= 1.25:
            return 0
        return next((n for n in range(-7, 8) if n and abs(q * 10.0 ** -n - 1) < 0.2), None)
    whole, fieldwise, scale = set(), collections.defaultdict(set), {}
    for (b, k), vs in vals.items():
        nk = f'{int(k[:4]) + 1}{k[4:]}'
        pairs = [('same', x, k, y, k) for i, x in enumerate(vs) for y in vs[i + 1:]] + \
                [('next', x, k, y, nk) for x in vs for y in vals.get((b, nk), [])]
        for kind, (j1, f1), k1, (j2, f2), k2 in pairs:
            comp = {f: pw(f1[f] / f2[f]) for f in FS if f1.get(f, 0) > 0 and f2.get(f, 0) > 0}
            off = {f: n for f, n in comp.items() if n}
            if not off:
                continue
            ones = [f for f, n in comp.items() if n == 0]
            if len(off) >= 2 and len(set(off.values())) == 1:
                n = next(iter(off.values()))
                for jj, kk, sign in ((j1, k1, 1), (j2, k2, -1)):  # the report without a unit word is the one to rescale
                    if reps[jj]['bases'][b].get('unit_missing') and kind == 'same':
                        fac = 10.0 ** (n * sign)
                        if any(abs(fac / sf - 1) < 0.01 for sf in (1e7, 1e2, 10, 1e4)):
                            scale[(jj, b)] = fac
                            break
                else:
                    whole |= {(j1, b, k1), (j2, b, k2)}
            elif len(off) == 1:
                f = next(iter(off))
                if kind == 'same' and ones:
                    fieldwise[(j1, b, k1)].add(f)
                    fieldwise[(j2, b, k2)].add(f)
                elif kind == 'same' or (not ones and abs(off[f]) >= 2 and f in ('sales', 'total_assets')):
                    whole |= {(j1, b, k1), (j2, b, k2)}
            else:
                whole |= {(j1, b, k1), (j2, b, k2)}
    touched = {jj for jj, b in scale} | {jj for jj, b, k in whole} | {jj for jj, b, k in fieldwise}
    for (jj, b), fac in scale.items():
        rescale_basis(reps[jj], b, fac)
        reps[jj]['bases'][b]['notes'][-1] = f'no unit on the statements: figures are in 1/{fac:g} crore (matches another report of the same year)'
    for jj, b, k in whole:
        y = reps[jj]['bases'][b]['years'][k]
        y['checks']['cross_unit'] = False
        y['helper'] = sorted(set(y['helper']) | set(NEED_BANK if reps[jj]['bases'][b].get('bank') else NEED))
    for (jj, b, k), fs in fieldwise.items():
        if (jj, b, k) in whole:
            continue
        y = reps[jj]['bases'][b]['years'][k]
        y['checks']['cross_field'] = sorted(fs)
        y['helper'] = sorted(set(y['helper']) | fs)
    for jj in touched:
        json.dump(reps[jj], open(jj, 'w', encoding='utf-8'), indent=1)
    return len(whole) + sum(1 for key in fieldwise if key not in whole)


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
    ap.add_argument('cmd', choices=['plan', 'fetch', 'reparse', 'refetch', 'queue', 'parse'])
    ap.add_argument('file', nargs='?')
    ap.add_argument('--rows')
    ap.add_argument('--groups', default='winner,fallen_winner')
    ap.add_argument('--syms')
    ap.add_argument('--gap', type=float, default=1.5)
    ap.add_argument('--tmp')
    ap.add_argument('--per', type=int, default=25)
    ap.add_argument('--fy', type=int)
    ap.add_argument('--keep-pdf')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    global KEEP_PDF
    KEEP_PDF = a.keep_pdf
    if a.cmd == 'plan':
        plan(a)
    elif a.cmd == 'fetch':
        fetch(a)
    elif a.cmd == 'reparse':
        reparse(a)
    elif a.cmd == 'refetch':
        refetch(a)
    elif a.cmd == 'queue':
        queue(a)
    else:
        if a.file.lower().endswith('.txt'):
            pgs = respread(read_pages_file(a.file))
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
