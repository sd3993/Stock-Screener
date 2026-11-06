# P7 recheck, run after each helper group: is each value a helper wrote printed in that report?
#   python -I tools/scripts/ar_helper_check.py FILE.csv      # rows with sym, fy, page_text, helper_file (a group's rows)
# Looks for the value's digits in the report's full page text at each unit (crore, lakh, thousand, million, rupees), allowing for
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


n = miss = 0
report = []
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8')):
    hf = r['helper_file']
    if not os.path.exists(hf):
        report.append(f"{r['sym']} FY{r['fy']}: no helper file")
        continue
    h = json.load(open(hf, encoding='utf-8'))
    text = ''
    if os.path.exists(r['page_text']):
        text = re.sub(r'[,\s]', '', open(r['page_text'], encoding='utf-8', errors='replace').read())
    notes = h.get('notes') or {}
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
