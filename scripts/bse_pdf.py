"""Downloads BSE announcement PDFs into data/companies/<SYM>/ in the project folder, extracts text with pdf_text.py,
and prints the lines that match a keyword pattern.

usage (from the project root): python scripts/bse_pdf.py SYM "regex" file1.pdf [file2.pdf ...]   (env MAXL = lines per file, default 40)
"""
import os, re, subprocess, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
sym, pat, files = sys.argv[1], re.compile(sys.argv[2], re.I), sys.argv[3:]
d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'companies', sym)
os.makedirs(d, exist_ok=True)
maxl = int(os.environ.get('MAXL', 40))
here = os.path.dirname(os.path.abspath(__file__))
for f in files:
    p = os.path.join(d, f)
    if not os.path.exists(p) or os.path.getsize(p) < 2000:
        for sub in ('AttachHis', 'AttachLive'):
            subprocess.run(['curl.exe', '-s', '-m', '60', '-o', p, 'https://www.bseindia.com/xml-data/corpfiling/%s/%s' % (sub, f)])
            if os.path.exists(p) and os.path.getsize(p) > 2000:
                break
    txt = p[:-4] + '.txt'
    if not os.path.exists(txt):
        subprocess.run([sys.executable, '-I', os.path.join(here, 'pdf_text.py'), p, '1', '50', txt], capture_output=True)
    print('=====', f, os.path.getsize(p) if os.path.exists(p) else 'missing')
    if not os.path.exists(txt):
        print('  (no text extracted)')
        continue
    lines = [l.strip() for l in open(txt, encoding='utf-8', errors='replace') if l.strip()]
    hits = [l for l in lines if pat.search(l)]
    for l in hits[:maxl]:
        print('  ' + l[:220])
