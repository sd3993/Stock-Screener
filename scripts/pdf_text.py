"""PDF to text with a page marker (<!-- page N -->) before each page; prints to stdout unless out.txt is given.

usage: pdf_text.py file.pdf [first_page] [last_page] [out.txt]  (1-based, inclusive; e.g. 1 9999 for the whole file)

Extractor: pypdf first. If pypdf raises any error (e.g. LimitReachedError on large PDFs), the whole requested range is
re-extracted with pymupdf (page.get_text()), so a file never mixes extractors. The extractor used is reported on stderr
('extractor pypdf' or 'extractor pymupdf (pypdf failed: <error>)'); output format and file naming are the same either way.
If both fail, prints 'error: ...' to stderr and exits 1 without writing out.txt.
"""
import sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
path = sys.argv[1]
a = int(sys.argv[2]) if len(sys.argv) > 2 else 1
b = int(sys.argv[3]) if len(sys.argv) > 3 else None


def with_pypdf():
    from pypdf import PdfReader
    r = PdfReader(path)
    n = len(r.pages)
    return n, [f'<!-- page {i + 1} -->\n' + (r.pages[i].extract_text() or '') for i in range(a - 1, min(b or n, n))]


def with_pymupdf():
    import pymupdf
    with pymupdf.open(path) as d:
        n = len(d)
        return n, [f'<!-- page {i + 1} -->\n' + (d[i].get_text() or '') for i in range(a - 1, min(b or n, n))]


try:
    n, out = with_pypdf()
    used = 'pypdf'
except Exception as e1:
    try:
        n, out = with_pymupdf()
        used = f'pymupdf (pypdf failed: {type(e1).__name__}: {e1})'
    except Exception as e2:
        print(f'error: cannot extract text from {path}: pypdf: {type(e1).__name__}: {e1}; pymupdf: {type(e2).__name__}: {e2}', file=sys.stderr)
        sys.exit(1)
text = '\n'.join(out)
if len(sys.argv) > 4:
    open(sys.argv[4], 'w', encoding='utf-8').write(text)
    print('pages', n, 'chars', len(text), 'written', sys.argv[4], 'extractor', used, file=sys.stderr)
else:
    print('extractor', used, file=sys.stderr)
    sys.stdout.reconfigure(encoding='utf-8')
    print(text)
