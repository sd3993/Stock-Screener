"""NSE investigation circulars (department INVG: SEBI orders, debarments, surveillance actions): keep them locally and search them by name.

Modes (run from the project root):
  fetch    uvx --from screener-mcp==0.5.0 --with pymupdf python scripts/nse_invg.py fetch [--from YYYY-MM] [--no-list]
           Refreshes data/market/nse_invg/list.json month by month from NSE's circulars feed (INVG department only; the feed
           is read through the screener library's NSE session, hence uvx), downloads every listed circular not yet on disk
           (PDF or ZIP, curl.exe from archives.nseindia.com) and extracts text once to <file>.txt beside it (a ZIP's .txt holds each
           member PDF under a '<!-- member: name -->' marker). Already-downloaded files are never fetched again.
             --from YYYY-MM   first month to list (default: the month of the newest listed circular, so the last month is re-read;
                              first-ever run: 2023-11)
             --no-list        skip the list refresh: download and extract only what list.json already names
             --retext         re-extract the text of every file (default: only files without a .txt)
           Files that cannot be fetched (not a PDF/ZIP) are written to index.json under "failed" and retried next run.
           Prints counts and the circulars whose PDFs have no text layer (scanned: the search cannot see them; no OCR is done).
  search   python -I scripts/nse_invg.py search [NAME ...] [--file names.txt] [--json out.json] [--max-lines N]
           Case-insensitive whole-phrase match of each name over every .txt (NAME arguments, plus one name per line from --file;
           blank lines and lines starting '#' ignored). Matching ignores case, punctuation, '&'/'and' spelling, extra whitespace and line
           breaks inside a phrase, and reads Pvt/Ltd as Private/Limited; the phrase must start and end on a word boundary. Prints per hit:
           circular id (INVGnnnnn), date, subject, name, and the matched line (a match across a line break shows both lines).
           --json writes {"hits": [{circular, date, subject, name, line}], "no_text_layer": [...]}.
           Exit codes: 0 = at least one hit, 1 = no hits, 2 = usage or data error (no names, empty data folder).
  names    uvx --from screener-mcp==0.5.0 python scripts/nse_invg.py names SYM [SYM ...] [--out file.json]
           Builds each company's search names: the company name (data/companies/<SYM>/scr/overview.json, "Ltd" kept as filed) and every
           promoter and promoter-group holder named in its latest filed shareholding-pattern XBRL (newest row of scr/shp_history.json;
           the XBRL is cached as scr/shp_latest.xml, fetched through the NSE session if absent). Named holders in institution
           categories (funds, insurers, banks, FPIs, NRIs, 'Details of ...' rows) are skipped. Needs scr/shp_history.json
           (scr_company.py SYM --only nse). Prints {sym: [names]}; --out writes it as JSON.
           A company without an XBRL (BSE-only listings) gets its company name alone and is named on stderr.
           Exit codes: 0 = all built, 1 = some company lacks an XBRL, 2 = usage error.
  run      python -I scripts/nse_invg.py run --names names.json --out runs/<RUN>/gate/invg_search_R5.json
           Runs the search for a names.json ({sym: [names]}) and writes {sym: {names, hits: [{circular, date, subject, name, line}]}}
           plus "_no_text_layer": [circular ids whose PDFs have no text], "_coverage": {circulars, files, newest_date}.
           Exit codes as search.

Data folder: data/market/nse_invg/  (list.json = the circular list, index.json = per-file status, <INVGnnnnn>.pdf|zip and .txt)
Coverage limits: only circulars NSE files under INVG; PDFs without a text layer are not searchable; a name written differently
in a circular (initials, spelling variants, a transliteration) is not matched.
"""
import sys

if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)

import asyncio
import bisect
import datetime as dt
import io
import json
import os
import re
import subprocess
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join('data', 'market', 'nse_invg')
LIST = os.path.join(DIR, 'list.json')
INDEX = os.path.join(DIR, 'index.json')
COMPANIES = os.path.join('data', 'companies')
FIRST = (2023, 11)


def jload(p, default):
    if not os.path.exists(p):
        return default
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def jsave(p, obj):
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ---------------------------------------------------------------- fetch
async def list_months(start, nse_get):
    rows = []
    y, m = start
    today = dt.date.today()
    while (y, m) <= (today.year, today.month):
        d0 = dt.date(y, m, 1)
        d1 = (d0.replace(day=28) + dt.timedelta(days=4))
        d1 = d1 - dt.timedelta(days=d1.day)
        r = None
        for _ in range(3):
            try:
                r = await nse_get('/api/circulars', {'fromDate': d0.strftime('%d-%m-%Y'), 'toDate': d1.strftime('%d-%m-%Y')})
                break
            except Exception:
                await asyncio.sleep(2)
        if r is None:
            raise SystemExit(f'error: circular list for {y}-{m:02d} could not be fetched')
        inv = [x for x in (r or {}).get('data', []) if x.get('fileDept') == 'INVG']
        print(f'{y}-{m:02d}: {len(r.get("data", []))} circulars, {len(inv)} INVG', flush=True)
        rows += inv
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        await asyncio.sleep(1)
    return rows


def merge_list(old, new):
    by = {x['circFilename']: x for x in old}
    dup = 0
    for x in new:
        if x['circFilename'] in by:
            dup += 1
        by[x['circFilename']] = x
    return sorted(by.values(), key=lambda x: (x['cirDate'], x['circFilename']), reverse=True), dup


def extract_text(path):
    """Text of a PDF, or of every PDF inside a ZIP (member marker lines); returns (text, pdf_count, empty_pdf_count)."""
    import fitz
    b = open(path, 'rb').read()
    docs = []
    if b.startswith(b'%PDF'):
        docs = [(None, b)]
    elif b.startswith(b'PK'):
        z = zipfile.ZipFile(io.BytesIO(b))
        docs = [(n, z.read(n)) for n in z.namelist() if n.lower().endswith('.pdf')]
    out, empty = [], 0
    for name, data in docs:
        try:
            t = ''.join(f'<!-- page {i + 1} -->\n' + p.get_text() for i, p in enumerate(fitz.open(stream=data, filetype='pdf')))
        except Exception as e:
            t = ''
            print(f'warning: {path}{":" + name if name else ""} unreadable: {e}', file=sys.stderr)
        if len(re.sub(r'<!-- page \d+ -->|\s', '', t)) < 100:
            empty += 1
        out.append((f'<!-- member: {name} -->\n' if name else '') + t)
    return '\n'.join(out), len(docs), empty


def download(url, path):
    u = url.replace('nsearchives.nseindia.in', 'archives.nseindia.com').replace('nsearchives.nseindia.com', 'archives.nseindia.com')
    subprocess.run(['curl.exe', '-s', '-m', '120', '-o', path, u], check=False)
    b = open(path, 'rb').read(4) if os.path.exists(path) else b''
    if not (b.startswith(b'%PDF') or b.startswith(b'PK')):
        if os.path.exists(path):
            os.remove(path)
        return False
    return True


def cmd_fetch(args):
    start = FIRST
    if '--from' in args:
        y, m = args[args.index('--from') + 1].split('-')
        start = (int(y), int(m))
    os.makedirs(DIR, exist_ok=True)
    lst = jload(LIST, [])
    if '--no-list' not in args:
        if '--from' not in args and lst:
            d = max(x['cirDate'] for x in lst)
            start = (int(d[:4]), int(d[4:6]))
        from screener_mcp.core.nse_client import get_nse_client

        async def go():
            nse = await get_nse_client()
            try:
                await nse.get_json('/api/marketStatus', {})
            except Exception as e:
                print('warm-up:', e)
            return await list_months(start, nse.get_json)
        new = asyncio.run(go())
        lst, dup = merge_list(lst, new)
        jsave(LIST, lst)
        print(f'list: {len(lst)} circulars ({dup} repeat listings merged)')
    idx = jload(INDEX, {'files': {}, 'failed': {}})
    idx['failed'] = {}
    got = 0
    for x in lst:
        fn = x['circFilename']
        p = os.path.join(DIR, fn)
        if not os.path.exists(p):
            if not download(x['circFilelink'], p):
                idx['failed'][fn] = x['circFilelink']
                continue
            got += 1
    retext = '--retext' in args
    for x in lst:
        fn = x['circFilename']
        p = os.path.join(DIR, fn)
        if not os.path.exists(p) or (os.path.exists(p + '.txt') and not retext and fn in idx['files']):
            continue
        t, n, empty = extract_text(p)
        with open(p + '.txt', 'w', encoding='utf-8') as f:
            f.write(t)
        idx['files'][fn] = {'pdfs': n, 'pdfs_without_text': empty}
    jsave(INDEX, idx)
    nt = sorted(k for k, v in idx['files'].items() if v['pdfs_without_text'])
    print(f'downloaded {got}; files {len(idx["files"])}; failed {len(idx["failed"])}; with a PDF lacking a text layer: {len(nt)}')
    for k in nt:
        print('  no text layer:', k, idx['files'][k])
    for k, u in idx['failed'].items():
        print('  failed:', k, u)


# ---------------------------------------------------------------- search
def norm(s):
    s = s.lower().replace('&amp;', '&').replace('&', ' and ')
    s = re.sub(r'[^0-9a-z]+', ' ', s)
    s = re.sub(r'\bpvt\b', 'private', s)
    s = re.sub(r'\bltd\b', 'limited', s)
    return re.sub(r'\s+', ' ', s).strip()


def corpus():
    lst = jload(LIST, [])
    if not lst or not os.path.isdir(DIR):
        raise SystemExit(f'error: no data in {DIR}; run fetch first')
    docs = []
    for x in lst:
        p = os.path.join(DIR, x['circFilename'] + '.txt')
        if not os.path.exists(p):
            continue
        lines = open(p, encoding='utf-8').read().split('\n')
        norm_lines = [norm(l) for l in lines]
        buf, starts = [], []
        pos = 0
        for nl in norm_lines:
            starts.append(pos)
            buf.append(nl)
            pos += len(nl) + 1
        docs.append((x, lines, ' '.join(buf), starts))
    return docs, lst


def search(names, docs):
    hits = []
    for x, lines, text, starts in docs:
        for name in names:
            q = norm(name)
            if not q or q not in text:  # cheap prefilter before the word-boundary regex
                continue
            for m in re.finditer(r'(?<![0-9a-z])' + re.escape(q) + r'(?![0-9a-z])', text):
                i = bisect.bisect_right(starts, m.start()) - 1
                j = bisect.bisect_right(starts, m.end() - 1) - 1
                line = ' / '.join(l.strip() for l in lines[i:j + 1] if l.strip())
                hits.append({'circular': x['circFilename'].rsplit('.', 1)[0], 'date': x['cirDate'], 'subject': x['sub'],
                             'name': name, 'line': line[:400]})
    seen, out = set(), []
    for h in hits:  # one row per circular, name and line
        k = (h['circular'], h['name'], h['line'])
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


def no_text():
    return sorted(k.rsplit('.', 1)[0] for k, v in jload(INDEX, {'files': {}})['files'].items() if v['pdfs_without_text'])


def read_names(path):
    return [l.strip() for l in open(path, encoding='utf-8') if l.strip() and not l.lstrip().startswith('#')]


def optval(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


def positional(args, flags_with_value):
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in flags_with_value:
            skip = True
        elif not a.startswith('--'):
            out.append(a)
    return out


def cmd_search(args):
    names = positional(args, {'--file', '--json', '--max-lines'})
    if optval(args, '--file'):
        names += read_names(optval(args, '--file'))
    if not names:
        print('error: no names (give NAME arguments or --file)', file=sys.stderr)
        return 2
    docs, lst = corpus()
    hits = search(names, docs)
    cap = int(optval(args, '--max-lines') or 1000)
    sys.stdout.reconfigure(encoding='utf-8')
    for h in hits[:cap]:
        print(f'{h["circular"]} | {h["date"]} | {h["subject"]} | {h["name"]} | {h["line"]}')
    print(f'{len(hits)} hit(s) over {len(docs)} texts ({len(lst)} circulars listed)', file=sys.stderr)
    if optval(args, '--json'):
        jsave(optval(args, '--json'), {'hits': hits, 'no_text_layer': no_text()})
    return 0 if hits else 1


def cmd_run(args):
    nm, out = optval(args, '--names'), optval(args, '--out')
    if not nm or not out:
        print('error: run needs --names and --out', file=sys.stderr)
        return 2
    names = jload(nm, None)
    if not names:
        print('error: names file empty or missing', file=sys.stderr)
        return 2
    docs, lst = corpus()
    res, total = {}, 0
    for sym, ns in names.items():
        h = search(ns, docs)
        total += len(h)
        res[sym] = {'names': ns, 'hits': h}
        print(f'{sym}: {len(ns)} names, {len(h)} hits')
    res['_no_text_layer'] = no_text()
    res['_coverage'] = {'circulars': len(lst), 'texts': len(docs), 'newest_date': max(x['cirDate'] for x in lst),
                        'oldest_date': min(x['cirDate'] for x in lst)}
    jsave(out, res)
    return 0 if total else 1


# ---------------------------------------------------------------- names
SKIP_CTX = re.compile(r'MutualFund|Insurance|Institution|Bank|Alternative|Venture|Provident|NBFC|Depositor|Sovereign|'
                      r'NonResidentIndians|ForeignPortfolio|^D_Details', re.I)


def holders(xml):
    out = []
    for c, n in re.findall(r'<in-bse-shp:NameOfTheShareholder[^>]*contextRef="([^"]+)"[^>]*>([^<]*)<', xml):
        n = n.replace('&amp;', '&').strip()
        if n and not SKIP_CTX.search(c) and n not in out:
            out.append(n)
    return out


def cmd_names(args):
    syms = positional(args, {'--out', '--file'})
    if not syms:
        print('error: no symbols', file=sys.stderr)
        return 2
    need = [s for s in syms if not os.path.exists(os.path.join(COMPANIES, s, 'scr', 'shp_latest.xml'))]
    fetched = {}
    if need:
        from screener_mcp.core.nse_client import get_nse_client

        async def go():
            nse = await get_nse_client()
            try:
                await nse.get_json('/api/marketStatus', {})
            except Exception:
                pass
            for s in need:
                p = os.path.join(COMPANIES, s, 'scr', 'shp_history.json')
                rows = (jload(p, {}).get('data') or {}).get('rows') or []
                if rows and rows[0].get('xbrl'):
                    fetched[s] = (await nse._client.get(rows[0]['xbrl'])).text
        asyncio.run(go())
    res, bad = {}, []
    for s in syms:
        p = os.path.join(COMPANIES, s, 'scr', 'shp_latest.xml')
        if s in fetched:
            open(p, 'w', encoding='utf-8').write(fetched[s])
        ov = (jload(os.path.join(COMPANIES, s, 'scr', 'overview.json'), {}).get('data') or {})
        names = [ov['name']] if ov.get('name') else []
        if os.path.exists(p):
            names += holders(open(p, encoding='utf-8').read())
        else:
            bad.append(s)  # BSE-only companies have no NSE XBRL: the company name alone is returned
        res[s] = names
    if optval(args, '--out'):
        jsave(optval(args, '--out'), res)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if bad:
        print('no shareholding-pattern XBRL for: ' + ', '.join(bad), file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    modes = {'fetch': cmd_fetch, 'search': cmd_search, 'names': cmd_names, 'run': cmd_run}
    if len(sys.argv) < 2 or sys.argv[1] not in modes:
        print(__doc__)
        sys.exit(2)
    sys.exit(modes[sys.argv[1]](sys.argv[2:]) or 0)
