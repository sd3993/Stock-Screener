import sys
from pypdf import PdfReader
# usage: pdf_text.py file.pdf [first_page] [last_page] [out.txt]  (1-based, inclusive)
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
