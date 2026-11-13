"""Tapetide REST client: every answer is cached in data/companies/<SYM>/api/ (market-wide ones in data/market/)
and every call is logged in data/calls.csv.
Token: the TAPETIDE_TOKEN environment variable (set by the user; never written to any file).
CLI:
  python scripts/tt.py usage
  python scripts/tt.py get /v1/stocks/TCS/shareholding [key=value ...] [--save PATH] [--all-pages]
  python scripts/tt.py calls [days]                 (calls per day from the log; days default 14)
  get prints the answer (first 20000 characters) unless --save PATH writes it to a file.
"""
import csv, datetime as dt, hashlib, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CALL_LOG, api_path, run_dir
BASE = 'https://api.tapetide.com'
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

class QuotaExceeded(Exception):
    pass

def now():
    return dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

def log_call(via, route, symbol, params, status):
    os.makedirs(os.path.dirname(CALL_LOG), exist_ok=True)
    new = not os.path.exists(CALL_LOG)
    with open(CALL_LOG, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['ts_ist', 'via', 'route', 'symbol', 'params', 'status', 'run'])
        try:
            run = os.path.basename(run_dir())
        except SystemExit:
            run = ''
        w.writerow([now(), via, route, symbol, json.dumps(params, ensure_ascii=False) if params else '', status, run])

def token():
    t = os.environ.get('TAPETIDE_TOKEN')
    if not t:
        raise SystemExit('TAPETIDE_TOKEN is not set: Tapetide is unreachable in this session; tell the user (sources/tapetide.md)')
    return t

def request(path, params=None, log=True, symbol=''):
    """One REST call. Returns the parsed JSON. Raises QuotaExceeded on 429."""
    params = {k: v for k, v in (params or {}).items() if v not in (None, '')}
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token(), 'Accept': 'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read().decode('utf-8'))
            if log:
                log_call('rest', path, symbol, params, 200)
            return body
        except urllib.error.HTTPError as e:
            if log:
                log_call('rest', path, symbol, params, e.code)
            if e.code == 429:
                raise QuotaExceeded(e.read().decode('utf-8', 'replace')[:300])
            if e.code >= 500 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f'HTTP {e.code} for {url}: {e.read().decode("utf-8", "replace")[:300]}')
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f'network error for {url}: {e}')

def get_all(path, params=None, symbol='', max_pages=50):
    """Follows meta.next_cursor; returns {'data': [...all items], 'meta': last meta, 'pages': n}."""
    params = dict(params or {})
    items, meta, pages = [], {}, 0
    while True:
        body = request(path, params, symbol=symbol)
        pages += 1
        data = body.get('data')
        items.extend(data if isinstance(data, list) else [data])
        meta = body.get('meta') or {}
        if not meta.get('next_cursor') or pages >= max_pages:
            break
        params['cursor'] = meta['next_cursor']
    return {'data': items, 'meta': meta, 'pages': pages}

def save(path, route, params, data, via='rest'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    env = {'fetched_at': now(), 'via': via, 'route': route, 'params': params, 'data': data}
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(env, fh, ensure_ascii=False, indent=1)
    return path

def cached(path, max_age_days=None):
    """The cached envelope if present (and younger than max_age_days), else None."""
    if not os.path.exists(path):
        return None
    env = json.load(open(path, encoding='utf-8-sig'))
    if max_age_days is not None:
        t = dt.datetime.strptime(env['fetched_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=IST)
        if (dt.datetime.now(IST) - t).days > max_age_days:
            return None
    return env

def fetch(sym, name, path, params=None, all_pages=False, max_age_days=None, refresh=False):
    """Cached fetch into data/companies/<SYM>/api/<name>.json. Returns the envelope."""
    out = api_path(sym, name)
    if not refresh:
        env = cached(out, max_age_days)
        if env is not None:
            return env
    data = get_all(path, params, symbol=sym) if all_pages else request(path, params, symbol=sym)
    save(out, path, params, data)
    return cached(out)

def usage():
    return request('/v1/me/usage', log=False)['data']

def sym_path(sym):
    return urllib.parse.quote(sym, safe='')

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

if __name__ == '__main__':
    a = sys.argv[1:]
    if {'-h', '--help'} & set(a):
        print(__doc__)
        sys.exit(0)
    if not a:
        sys.exit(__doc__ or 'usage: see the header of this file')
    if a[0] == 'usage':
        u = usage()
        print(f"plan {u.get('plan')}; today {u['day']['used']}/{u['day']['limit']} (resets {u['day']['resets_at']}); month {u['month']['used']}/{u['month']['limit']}")
    elif a[0] == 'get':
        route, rest = a[1], a[2:]
        params = dict(x.split('=', 1) for x in rest if '=' in x and not x.startswith('--'))
        out = rest[rest.index('--save') + 1] if '--save' in rest else None
        data = get_all(route, params) if '--all-pages' in rest else request(route, params)
        if out:
            save(out, route, params, data)
            print('saved', out)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=1)[:20000])
    elif a[0] == 'calls':
        days = int(a[1]) if len(a) > 1 else 14
        from collections import Counter
        c = Counter()
        if os.path.exists(CALL_LOG):
            for r in csv.DictReader(open(CALL_LOG, encoding='utf-8-sig')):
                c[(r['ts_ist'][:10], r['via'])] += 1
        for (d, via), n in sorted(c.items())[-days * 2:]:
            print(d, via, n)
    else:
        sys.exit('unknown command ' + a[0])
