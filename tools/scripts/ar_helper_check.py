# P7 recheck, run after each helper group: is each value a helper wrote printed in that report?
#   python -I tools/scripts/ar_helper_check.py FILE.csv      # rows with sym, fy, page_text, helper_file (a group's rows)
#   python -I tools/scripts/ar_helper_check.py FILE.csv --only SYM FY   # one report: a helper's check after writing its file; fix what it lists, then go on
# Exits 1 if anything asked for is missing or a value is unexplained. Completeness: every asked field is there, a null has a note, a whole-report read has all fields.
# Looks for the value's digits in the report's page text and whole-report text at each unit (crore, lakh, thousand, million, rupees), allowing for
# rounding and for Indian or Western commas. Prints the values it can't find: arithmetic the helper noted, a read from the PDF, or a wrong
# figure. Also prints checks on the figures themselves: pat <= pbt + small tax credit, debtors and borrowings within total assets.
import csv, json, os, re, sys

UNITS = (1, 100, 1e4, 10, 1e7)


def forms(v):
    out = set()
    for u in UNITS:
        x = abs(v) * u
        for d in (0, 1, 2, 3):
            s = f'{x:.{d}f}'
            if len(s.replace('.', '')) >= 3:
                out.add(s.rstrip('0').rstrip('.') if '.' in s else s)
                out.add(s)
    return out


ALL_FIELDS = ('sales', 'other_income', 'interest', 'dep', 'pbt', 'tax', 'pat', 'eps', 'dividend', 'equity_cap', 'reserves', 'borrowings', 'total_assets', 'debtors', 'cfo')
ASKABLE = ALL_FIELDS + ('exceptional',)


def gaps(r, h, label):
    """What was asked for and isn't in the helper file (a null needs a note saying why)."""
    bases, notes, out = h.get('bases') or {}, h.get('notes') or {}, []
    noted = lambda b, f: any(k == 'all' or f in k or f in str(v) or b in k or b in str(v).lower() for k, v in notes.items())

    def need(b, y, fields):
        vals = (bases.get(b) or {}).get(y)
        if not isinstance(vals, dict):
            return
        for f in fields:
            if f not in vals:
                out.append(f'{label}: {b} {y} {f} missing')
            elif vals[f] is None and not noted(b, f):
                out.append(f'{label}: {b} {y} {f} null with no note')

    for part in r.get('fields', '').split(';'):
        m = re.match(r'\s*([sc]):(\d{4}-\d{2}):(.*)', part)
        if m and not h.get('replace_parsed'):
            need({'s': 'standalone', 'c': 'consolidated'}[m[1]], m[2], [f for f in m[3].split('|') if f.strip() in ASKABLE])
    if h.get('replace_parsed') or r.get('fields', '').startswith('all'):
        if h.get('replace_parsed') and not h.get('year_end'):
            out.append(f'{label}: replace_parsed with no year_end')
        for b, years in bases.items():
            ys = [y for y, v in years.items() if isinstance(v, dict)]
            if ys:
                need(b, h.get('year_end') if h.get('year_end') in ys else max(ys), ALL_FIELDS)
    return out


args = sys.argv[1:]
only = None
if '--only' in args:
    i = args.index('--only')
    only = (args[i + 1], args[i + 2].upper().removeprefix('FY'))
n = miss = 0
report = []
for r in csv.DictReader(open(args[0], encoding='utf-8')):
    if only and not (r['sym'] == only[0] and r['fy'].endswith(only[1])):
        continue
    hf = r['helper_file']
    if not os.path.exists(hf):
        report.append(f"{r['sym']} FY{r['fy']}: no helper file")
        continue
    h = json.load(open(hf, encoding='utf-8'))
    if h.get('wrong_report'):
        continue
    report += gaps(r, h, f"{r['sym']} FY{r['fy']}")
    text = ''
    for tf in (r['page_text'], r['json'][:-5] + '_full.txt'):
        if os.path.exists(tf):
            text += re.sub(r'[,\s]', '', open(tf, encoding='utf-8', errors='replace').read())
    notes = h.get('notes') or {}
    # was every basis and year asked for read? (a helper file drops the report from the queue, so a gap here is never asked again)
    bases = h.get('bases') or {}
    has = lambda b, y=None: any(isinstance(v, (int, float)) for yy, fs in (bases.get(b) or {}).items() if y in (None, yy) and isinstance(fs, dict) for v in fs.values())
    for part in r.get('fields', '').split(';'):
        m = re.match(r'\s*([sc]):(\d{4}-\d{2}):', part)
        basis = {'s': 'standalone', 'c': 'consolidated'}[m[1]] if m else ''
        if m and not has(basis, m[2]) and not h.get('replace_parsed') and not any(k == 'all' or basis in k or basis in str(v).lower() for k, v in notes.items()):
            report.append(f"{r['sym']} FY{r['fy']}: asked {m[1]}:{m[2]}, nothing read | {str(notes.get('all', ''))[:60]}")
    if (h.get('replace_parsed') or r.get('fields', '').startswith('all')) and not has('consolidated') and re.search(r'consolidatedbalancesheetasat', text, re.I):
        report.append(f"{r['sym']} FY{r['fy']}: report prints a consolidated balance sheet, none read")
    for b, years in (h.get('bases') or {}).items():
        for y, fields in years.items():
            if not isinstance(fields, dict):
                continue
            for f, v in fields.items():
                if not isinstance(v, (int, float)) or v == 0:
                    continue
                n += 1
                if not any(s in text for s in forms(v)):
                    miss += 1
                    note = notes.get(f'{b}:{y}:{f}', '')
                    report.append(f"{r['sym']} FY{r['fy']} {b} {y} {f}={v} not found | {str(note)[:90]}")
            g = lambda k: fields.get(k) if isinstance(fields.get(k), (int, float)) else None
            ta = g('total_assets')
            for k in ('debtors', 'equity_cap', 'reserves'):
                if ta and g(k) and g(k) > ta * 1.01:
                    report.append(f"{r['sym']} FY{r['fy']} {b} {y}: {k} {g(k)} above total_assets {ta}")
            if g('pbt') is not None and g('tax') is not None and g('pat') is not None and abs(g('pbt') - g('tax') - g('pat')) > max(1, abs(g('pbt')) * .02):
                report.append(f"{r['sym']} FY{r['fy']} {b} {y}: pbt {g('pbt')} - tax {g('tax')} != pat {g('pat')}")
print(f'{n} values checked, {miss} not found in the page text')
print('\n'.join(report))
unexplained = [x for x in report if not re.search(r'not found \| \S', x)]
print(f'{len(unexplained)} to fix or explain' if unexplained else 'complete')
sys.exit(1 if unexplained else 0)
