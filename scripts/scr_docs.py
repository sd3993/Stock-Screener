"""S8 downloads from the company's saved screener answers (run scr_company.py first): results filings (last 8),
investor presentations and call transcripts (last 6 quarters), governance and business filings (3 years) from the
NSE announcements; annual reports (last 3) and exchange-hosted transcripts from the document list. PDFs with text,
into data/companies/<SYM>/<FYyyQn>/, recorded in index.json; nothing indexed is downloaded again. An index entry whose
file is not on disk is dropped and the file fetched again; a failed download is listed once under missing; an annual
report without a numeric year (screener's "Unknown") is skipped. NSE archive links (.com and .in) go to archives.nseindia.com.
  python scripts/scr_docs.py SYM
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

def url_id(url):
    """Short file id from an exchange or document link, without its extension."""
    name = url.split('Pname=')[-1] if 'Pname=' in url else url.rsplit('/', 1)[-1]
    return re.sub(r'\W', '', re.sub(r'\.pdf$', '', name, flags=re.I))[:40]

def load_index(sym):
    p = os.path.join(FILINGS_DIR, sym, 'index.json')
    if os.path.exists(p):
        idx = json.load(open(p, encoding='utf-8-sig'))
        idx.setdefault('files', []); idx.setdefault('missing', []); idx.setdefault('fetched_direct', [])
        # an entry whose file is not on disk is dropped, so the file is fetched again (and never used as a duplicate)
        gone = [f for f in idx['files'] if not f.get('file') or
                not os.path.exists(os.path.join(FILINGS_DIR, sym, f['file'].replace(chr(92), '/')))]
        if gone:
            print(f'{sym}: {len(gone)} indexed files not on disk; their entries dropped and refetched')
            idx['files'] = [f for f in idx['files'] if f not in gone]
        return idx
    return {'sym': sym, 'files': [], 'missing': [], 'fetched_direct': []}

def save_index(sym, idx):
    p = os.path.join(FILINGS_DIR, sym, 'index.json')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(idx, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def download(url, dest):
    """Free download (document links, exchange PDFs) with curl; returns sha256 or None."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(['curl.exe', '-s', '-L', '-m', '120', '-o', dest, '-w', '%{http_code}', url], capture_output=True, text=True)
    if r.stdout.strip() != '200' or not os.path.exists(dest) or os.path.getsize(dest) < 200:
        if os.path.exists(dest):
            os.remove(dest)
        return None
    head = open(dest, 'rb').read(512).lstrip().lower()
    if dest.lower().endswith('.pdf') and not head.startswith(b'%pdf'):
        os.remove(dest)  # an HTML error page, not the PDF
        return None
    return hashlib.sha256(open(dest, 'rb').read()).hexdigest()

def have(idx, url):
    return any(f.get('source_url') == url for f in idx['files'])

def get(sym, idx, url, quarter, fname, typ, period, filed, source, ident, text=False):
    """Download url into data/companies/<SYM>/<quarter>/<fname> unless indexed; returns the path or None."""
    if not url or have(idx, url):
        return None
    rel = os.path.join(quarter, fname)
    dest = os.path.join(FILINGS_DIR, sym, rel)
    sha = download(url, dest)
    if not sha:
        m = {'what': f'{typ} {period} {filed}', 'tried': url}
        if m not in idx['missing']:
            idx['missing'].append(m)
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

sym = sys.argv[1]
base = os.path.join('data', 'companies', sym, 'scr')
load = lambda n: (json.load(open(os.path.join(base, n + '.json'), encoding='utf-8'))['data']
                  if os.path.exists(os.path.join(base, n + '.json')) else {})
today = dt.date.today()
GOV = re.compile(r'auditor|preferential|qip|warrant|reg(ulation)?\.? ?(7|29|31)|sast|substantial acquisition|pledge|'
                 r'encumbr|credit rating|sebi|show cause|penalt|fine|litigation|court|tribunal|nclt|related party|resign|'
                 r'fraud|forensic|default|insolvency|order|contract|acquisition|merger|demerger|amalgamation|buyback|'
                 r'rights issue|allotment|change in (director|management|kmp)|cessation|appointment', re.I)

def nse(url):  # nsearchives.nseindia.com / .in hang for curl; archives.nseindia.com serves the same paths
    return url.replace('://nsearchives.nseindia.com/', '://archives.nseindia.com/').replace('://nsearchives.nseindia.in/', '://archives.nseindia.com/')

def day(s):
    try:
        return dt.datetime.strptime(s[:11], '%d-%b-%Y').date()
    except (TypeError, ValueError):
        return parse_date(s)

idx = load_index(sym)
n, skipped = 0, []
res, calls, gov = [], [], []
for a in load('announcements').get('announcements', []):
    d, url = day(a.get('date')), a.get('url')
    if not d or not str(url).startswith('http'):  # exchange queries (volume/price moves) carry no file
        continue
    cat, nc, head = a.get('category') or '', a.get('nse_category') or '', a.get('headline') or ''
    if re.search(r'outcome of board meeting|financial result', nc, re.I) and re.search(r'financial result', head, re.I) \
            and not re.search(r'newspaper|intimation', nc + head, re.I):
        res.append((d, url, 'results', head))
    elif re.search(r'investor presentation|analysts?/institutional investor meet|con\.? ?call|transcript', nc + ' ' + head, re.I):
        if (today - d).days <= 550 and not re.search(r'intimation|schedule', head, re.I) or re.search(r'transcript', head, re.I):
            calls.append((d, url, 'earnings_call', head))
    elif cat in ('insider_trading', 'acquisition', 'fund_raise', 'credit_rating', 'buyback') or GOV.search(nc + ' ' + head):
        gov.append((d, url, 'filing:' + (cat or 'other'), head))
for d, url, typ, head in res[:8] + calls + gov[:120]:
    q = reported_quarter(d) if typ in ('results', 'earnings_call') else fy_quarter(d)
    ident = url_id(url)
    src = 'bse' if 'bseindia' in url else 'nse' if 'nseindia' in url else 'web'
    kind = typ.split(':')[0]
    n += bool(get(sym, idx, nse(url), q, f'{kind}_{d.isoformat()}_{ident}.pdf', typ, head[:120], d, src, ident, text=True))
docs = load('documents')
for r in docs.get('annual_reports', [])[:3]:
    url, y = r.get('url') or '', r.get('year')
    if not url or not str(y or '').isdigit() or not url.lower().endswith('.pdf'):  # screener gives "Unknown" for some years
        skipped.append(f"annual report {y}: {url or 'no link'}")
        continue
    q = f'FY{int(y) % 100:02d}Q4'
    ident = url_id(url)
    n += bool(get(sym, idx, url, q, f'annual_report_FY{y}_{ident}.pdf', 'annual_report', f'FY{y}',
                  dt.date(int(y), 3, 31), 'bse' if 'bseindia' in url else 'web', ident, text=True))
for r in docs.get('earnings_calls', [])[:6]:
    url, d = r.get('url') or '', parse_date(r.get('quarter'))  # "Aug 2026": the call's month
    if not d or not re.search(r'bseindia|nseindia', url):
        skipped.append(f"transcript {r.get('quarter')}: not an exchange link ({url or 'none'})")
        continue
    ident = url_id(url)
    n += bool(get(sym, idx, nse(url), reported_quarter(d), f'transcript_{d.isoformat()}_{ident}.pdf',
                  'transcript', r.get('quarter'), d, 'bse' if 'bseindia' in url else 'nse', ident, text=True))
idx['last_fetched'] = today.isoformat()
save_index(sym, idx)
print(f'{sym}: announcements -> results {len(res)}, presentations/calls {len(calls)}, governance {len(gov)}; '
      f'files downloaded {n}; missing {len(idx["missing"])}; skipped {len(skipped)}')
for s in skipped:
    print('  skipped', s)
