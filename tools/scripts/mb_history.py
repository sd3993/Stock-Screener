import asyncio, csv, datetime as dt, json, os, sys, time
# Multibagger study, P1.1 (process/past/p1_universe.md): long price and valuation history per company from screener.in's public chart API
# (no login, no model tokens), back to about 2005: price and volume, P/E with the TTM EPS behind it, and market cap to
# sales with TTM sales (market cap = the ratio x sales). Saved as data/companies/<SYM>/scr/history.json; a company already
# saved is skipped unless --refresh, or --recheck-empty (re-fetches saved companies with a series that has no values, unless the standalone series were
# already checked). --workers N fetches N companies at once (default 1); the library's shared pacing and 429 cooldown still apply. Input: symbols, or a CSV with columns sym and (optionally) screener_id.
#   uvx --from screener-mcp==0.5.0 python tools/scripts/mb_history.py SYM ... | --csv runs/past/<date>/universe.csv [--refresh | --recheck-empty] [--workers N]
# Starts 1.2 s between requests, where screener stopped answering 429 at the same throughput as the library's 0.25 s
# (3 Nov 2026), and adds 0.05 s after each cooldown, up to 3 s, in case its limit tightens.
os.environ.setdefault('SCREENER_MIN_INTERVAL', '1.2')
if '--login' not in sys.argv:  # public mode by default, even when the screener login is in the environment (tools/tools.md)
    for k in ('SCREENER_USERNAME', 'SCREENER_PASSWORD'):
        os.environ.pop(k, None)
import screener_mcp.client as sc
from screener_mcp.client import get_client
from screener_mcp.core.company_page import fetch_company_page

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
QUERIES = {'price': 'Price-Volume', 'pe': 'Price to Earning-Median PE-EPS',
           'mcap_sales': 'Market Cap to Sales-Median Market Cap to Sales-Sales'}
a = sys.argv[1:]
refresh, recheck = '--refresh' in a, '--recheck-empty' in a
workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 1
if '--csv' in a:
    todo = [(r['sym'], r.get('screener_id') or None) for r in csv.DictReader(open(a[a.index('--csv') + 1], encoding='utf-8'))]
else:
    skip = {a.index('--workers') + 1} if '--workers' in a else set()
    todo = [(s, None) for i, s in enumerate(a) if not s.startswith('--') and i not in skip]

def has_data(ds):  # the chart answers every date, with None where there's no value
    return any(p[1] not in (None, '') for v in ds.values() for p in (v or []) if len(p) > 1)

async def one(client, sym, cid):
    out = os.path.join('data', 'companies', sym, 'scr', 'history.json')
    if os.path.exists(out) and not refresh:
        if not recheck:
            return 'cached'
        old = json.load(open(out, encoding='utf-8'))
        if old.get('standalone_checked') or all(has_data((old['data'].get(k) or {}).get('datasets') or {}) for k in QUERIES):
            return 'cached'
        cid = cid or old['args'].get('company_id')
    if not cid:
        cid = (await fetch_company_page(sym, 'consolidated')).company_id
    series = {}
    for key, q in QUERIES.items():
        for consolidated in (True, False):  # consolidated where the company files it, else standalone
            # standalone = no consolidated parameter at all: any value, even '' or 'false', returns the consolidated series
            params = {'q': q, 'days': 10000, **({'consolidated': 'true'} if consolidated else {})}
            r = await client.get_json(f'/api/company/{cid}/chart/', params=params)
            ds = {d.get('metric') or d.get('label'): d.get('values') for d in (r or {}).get('datasets', [])}
            if has_data(ds):
                series[key] = {'consolidated': consolidated, 'datasets': ds}
                break
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({'fetched_at': dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'screener-public',
               'tool': 'chart', 'args': {'symbol': sym, 'company_id': cid, 'days': 10000}, 'standalone_checked': True, 'data': series},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    return 'saved'

async def main():
    client = await get_client()
    n429 = [0]
    cool = client._cool_down
    def counted(sec):  # count 429/503 cooldowns and widen the gap between requests
        n429[0] += 1
        sc._MIN_INTERVAL = min(sc._MIN_INTERVAL + 0.05, 3.0)
        cool(sec)
    client._cool_down = counted
    counts, failed, q, t0 = {}, [], asyncio.Queue(), time.monotonic()
    for x in todo:
        q.put_nowait(x)
    done = [0]
    async def worker():
        while not q.empty():
            sym, cid = q.get_nowait()
            try:
                k = await one(client, sym, cid)
                counts[k] = counts.get(k, 0) + 1
            except Exception as e:  # one company's failure doesn't stop the run; re-run to retry
                failed.append(f'{sym}: {type(e).__name__}: {e}'[:200])
            done[0] += 1
            if done[0] % 100 == 0:
                print(f'{done[0]}/{len(todo)} {counts} failed {len(failed)} cooldowns {n429[0]} gap {sc._MIN_INTERVAL:.2f}s '
                      f'{int(time.monotonic() - t0)}s', flush=True)
    await asyncio.gather(*(worker() for _ in range(workers)))
    print(f'done {len(todo)}: {counts}; failed {len(failed)}; cooldowns {n429[0]}; gap {sc._MIN_INTERVAL:.2f}s')
    for f in failed[:50]:
        print('  ', f)

asyncio.run(main())
