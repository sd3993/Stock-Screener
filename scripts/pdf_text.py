"""PDF to text with a page marker (<!-- page N -->) before each page; prints to stdout unless out.txt is given.

usage: pdf_text.py file.pdf [first_page] [last_page] [out.txt]  (1-based, inclusive; e.g. 1 9999 for the whole file)
"""
import sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
n = len(r.pages)
a = int(sys.argv[2]) if len(sys.argv) > 2 else 1
b = int(sys.argv[3]) if len(sys.argv) > 3 else n
out = []
for i in range(a - 1, min(b, n)):
    out.append(f'<!-- page {i + 1} -->\n' + (r.pages[i].extract_text() or ''))
text = '\n'.join(out)
if len(sys.argv) > 4:
    open(sys.argv[4], 'w', encoding='utf-8').write(text)
    print('pages', n, 'chars', len(text), 'written', sys.argv[4], file=sys.stderr)
else:
    sys.stdout.reconfigure(encoding='utf-8')
    print(text)
