"""Shared helpers (scr_docs.py uses the downloads): reads Tapetide's filings and documents lists (REST or MCP shapes),
downloads documents into data/companies/<SYM>/<FYyyQn>/ and records them in index.json (principles/data_rules.md).
No command line of its own: import it (python -I, from the project root) and call its functions; running it does nothing.
"""
import datetime as dt, json, os, re, subprocess, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt
from config import COMPANIES_DIR as FILINGS_DIR

def fy_quarter(d):
    """Quarter label of the quarter that contains date d, e.g. 2026-08-10 -> FY27Q2."""
    q = {4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3, 1: 4, 2: 4, 3: 4}[d.month]
    fy = d.year + 1 if d.month >= 4 else d.year
    return f'FY{fy % 100:02d}Q{q}'

def reported_quarter(d):
    """Quarter a results filing, transcript or presentation filed on date d reports: the one ended before d."""
    return fy_quarter(dt.date(d.year, ((d.month - 1) // 3) * 3 + 1, 1) - dt.timedelta(days=1))

def parse_date(s):
    if not s:
        return None
    s = str(s)[:10]
    for f in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    m = re.match(r'([A-Za-z]{3}) (\d{4})', s)  # "Aug 2026"
    if m:
        return dt.datetime.strptime('01 ' + m.group(0), '%d %b %Y').date()
    return None

def items(env):
    """List of items from a cached envelope, whatever the response shape."""
    d = env['data'] if env else []
    if isinstance(d, dict):
        d = d.get('data', d)
    if isinstance(d, dict):
        for k in ('documents', 'filings', 'items', 'results'):
            if isinstance(d.get(k), list):
                return d[k]
    if isinstance(d, list) and d and isinstance(d[0], dict) and 'documents' in d[0]:
        return [x for page in d for x in page['documents']]
    return d if isinstance(d, list) else []

def f_date(x):
    return parse_date(x.get('date') or x.get('filing_date') or x.get('filed_at') or x.get('doc_date') or x.get('period'))

def f_url(x):
    links = x.get('links') or {}
    return (x.get('url') or x.get('document_url') or x.get('attachment_url') or x.get('pdf_url') or links.get('pdf_url')
            or x.get('source_url'))

def url_id(url):
    """Short file id from an exchange or document link, without its extension."""
    name = url.split('Pname=')[-1] if 'Pname=' in url else url.rsplit('/', 1)[-1]
    return re.sub(r'\W', '', re.sub(r'\.pdf$', '', name, flags=re.I))[:40]

def ar_quarter(doc, d):
    """Annual reports carry period "FY2026" and a placeholder date (2026-01-01): file them under FY26Q4."""
    m = re.search(r'(?:FY|Year |Report )(\d{4})', f"{doc.get('period') or ''} {doc.get('title') or ''}")
    if m:
        return f'FY{int(m.group(1)) % 100:02d}Q4'
    return fy_quarter(dt.date(d.year - 1 if d.month < 4 else d.year, 3, 31))

def load_index(sym):
    p = os.path.join(FILINGS_DIR, sym, 'index.json')
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8-sig'))
    return {'sym': sym, 'files': [], 'missing': [], 'fetched_direct': []}

def save_index(sym, idx):
    p = os.path.join(FILINGS_DIR, sym, 'index.json')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(idx, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def have(idx, url):
    return any(f.get('source_url') == url for f in idx['files'])

def get(sym, idx, url, quarter, fname, typ, period, filed, source, ident, text=False):
    """Download url into data/companies/<SYM>/<quarter>/<fname> unless indexed; returns the path or None."""
    if not url or have(idx, url):
        return None
    rel = os.path.join(quarter, fname)
    dest = os.path.join(FILINGS_DIR, sym, rel)
    sha = tt.download(url, dest)
    if not sha:
        idx['missing'].append({'what': f'{typ} {period} {filed}', 'tried': url})
        return None
    dup = next((f for f in idx['files'] if f.get('sha256') == sha), None)
    if dup:
        os.remove(dest)
        rel = dup['file']
    txt = None
    if text and dest.lower().endswith('.pdf') and not dup:
        txt = rel.replace('\\', '/') + '.txt'
        subprocess.run([sys.executable, 'scripts/pdf_text.py', dest, '1', '9999', dest + '.txt'], capture_output=True)
    idx['files'].append({'file': rel.replace('\\', '/'), 'quarter': quarter, 'type': typ, 'period': period,
                         'filed_date': str(filed), 'source': source, 'id': ident, 'source_url': url, 'sha256': sha,
                         'text_file': txt, 'scanned': None})
    return dest

def get_parsed_doc(sym, idx, doc, with_pdf=False):
    """A parsed Tapetide document: Markdown always, PDF too when asked."""
    links = doc.get('links') or {}
    d = f_date(doc)
    if not d or not links.get('markdown_url'):
        return 0
    typ = doc.get('doc_type', 'doc')
    q = ar_quarter(doc, d) if typ == 'annual_report' else reported_quarter(d)
    n = 0
    stem = f"{typ}_{d.isoformat()}_{doc.get('doc_id')}"
    n += bool(get(sym, idx, links['markdown_url'], q, stem + '.md', typ, doc.get('period'), d, 'tapetide', doc.get('doc_id')))
    if with_pdf and links.get('pdf_url'):
        n += bool(get(sym, idx, links['pdf_url'], q, stem + '.pdf', typ, doc.get('period'), d, 'tapetide', doc.get('doc_id')))
    return n
