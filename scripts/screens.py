"""S2 (workflow/s2_screens.md): the market screens and whole-market sweep, and the universe built from their pages.
If screener.in can't be reached: sources/screener.md.
  uvx --from screener-mcp==0.5.0 python scripts/screens.py run [--only T3,B05,Q1B02] [--probe-only]   (logged in)
  python -I scripts/screens.py build        (universe.csv from the saved pages; also run by "run" after each query)
run: the column probe, the query-field probes and groups, then every idea screen, whole-market band and extra sweep, each
  page saved straight to its file, and the universe rebuilt and checked after each query. Screens need the screener
  login from the environment (sources/screener.md); no JSON on the command line, so any shell works.
build: <run>/universe.csv from every saved page in <run>/screens/ (<ID>_<desc|asc>_p<NN>.json): one row per symbol with
  hits (the T screens it matched), in_sweep (in a B band) and every field found under screener's names (Q pages only add
  fields); warns (exit 1) when a query's saved companies don't add up to its total or a column of screens.json never
  came back.
run inputs: workflow/screens.json (screens, base, bands, columns, query_fields); the run folder (config.py).
Outputs in <run>/screens/: _probe/columns.json and _probe/<field>.json (count probes), _groups.json (counts, which
  query fields came back on the column row, the groups sharing an extra sweep, the bands), <ID>_<desc|asc>_p<NN>.json
  per page (IDs: T<n> screens, B<nn> bands, Q<g>B<nn> extra sweeps); <run>/universe.csv (build); a summary
  table (ID, total, pages, companies saved) at the end.
Every query: limit 200, min_market_cap 0, exclude_flagged false, sorted by Market Capitalization; a query of T rows takes
  desc pages 1..max(1, floor(T/200)), then asc page 1 when T > 200 and T isn't a multiple of 200 (sources/screener.md).
  A band under 200 rows is complete on its one page and is not merged (merging only saved calls when paging by hand).
Resumable: saved pages, probes and _groups.json are reused (delete _groups.json to redo the grouping). A page is saved
  only when screener answered ok and not partial (temp file, then rename). A failed call waits 60 s and retries twice,
  then the script stops with the reason (exit 2), keeping every saved page. It stops (exit 3) when a column in
  screens.json is missing from the account's column set (named), or when the universe check finds that a query's
  saved rows don't add up to its total; the "columns never returned" warning counts only after the last query.
"""
import argparse, asyncio, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scr_tool
import wf_lib as W
from config import run_dir

LIMIT, WAIT, RETRIES = 200, 60, 2
SORT = 'Market Capitalization'
ANY = '> -9999999'  # a condition every non-empty value meets: names the field so it comes back


class Stop(Exception):
    pass


def args_for(query, order='desc', page=1, limit=LIMIT):
    return {'query': query, 'limit': limit, 'sort_by': SORT, 'order': order, 'page': page,
            'min_market_cap': 0, 'exclude_flagged': False}


def valid(path):
    try:
        with open(path, encoding='utf-8') as fh:
            env = json.load(fh)
        d = env.get('data')
        return env if isinstance(d, dict) and 'total_matches' in d and isinstance(d.get('results'), list) and not env.get('partial') else None
    except (OSError, ValueError):
        return None


async def fetch(path, args, log):
    """A saved page, or one fetched now (ok answers only), with WAIT s and RETRIES retries on failure."""
    env = valid(path)
    if env:
        return env['data'], False
    last = ''
    for attempt in range(RETRIES + 1):
        if attempt:
            log(f'  retry {attempt}/{RETRIES} in {WAIT} s: {last}')
            await asyncio.sleep(WAIT)
        try:
            env, ok, status = await scr_tool.call('screen_stocks', args)
        except Exception as e:  # dropped connection, 429 raised by the client
            ok, status, env = False, f'{type(e).__name__}: {e}', None
        if ok and not env.get('partial') and isinstance(env.get('data'), dict) and 'total_matches' in env['data']:
            scr_tool.save(env, path)
            return env['data'], True
        last = (status if env is None else f"{status}{' (partial)' if env.get('partial') else ''}: "
                f"{(env.get('warnings') or ['no reason given'])[-1]}")[:300]
    raise Stop(f'{os.path.basename(path)}: screener failed {RETRIES + 1} times: {last}')


def bands(cfg):
    b = cfg['bands']
    out = [(lo, hi) for lo, hi in zip(b, b[1:])] + [(b[-1], None)]
    return [(f'B{i:02d}', lo, hi) for i, (lo, hi) in enumerate(out, 1)]


def band_query(base, lo, hi):
    return f'{base} AND Market Capitalization >= {lo}' + (f' AND Market Capitalization < {hi}' if hi is not None else '')


async def probe(cfg, sdir, log):
    """Column check and query-field groups; returns the groups (list of field lists)."""
    gp = os.path.join(sdir, '_groups.json')
    pdir = os.path.join(sdir, '_probe')
    if os.path.exists(gp):
        g = json.load(open(gp, encoding='utf-8'))
        log(f'groups reused from {gp}: {g["groups"]}')
        return g['groups']
    base = cfg['base']
    d, _ = await fetch(os.path.join(pdir, 'columns.json'), args_for(band_query(base, 1000, 1100), limit=1), log)
    rows = d.get('results') or []
    if not rows:
        raise Stop('column probe returned no row (base AND market cap 1000-1100): check the query and the login')
    got = set((rows[0].get('fundamentals') or {}).keys())
    missing = [c for c in cfg['columns'] if c not in got]
    if missing:
        raise Stop(f'COLUMNS MISSING from the account column set: {missing} (sources/screener.md); fix the column set or screens.json')
    on_row = [f for f in cfg.get('query_fields', []) if f in got]
    rest = [f for f in cfg.get('query_fields', []) if f not in got]
    counts = {}
    for f in rest:
        d, _ = await fetch(os.path.join(pdir, re.sub(r'\W+', '_', f) + '.json'), args_for(f'{base} AND {f} {ANY}', limit=1), log)
        counts[f] = d['total_matches']
    groups, combos = [], {}
    for f in sorted(rest, key=lambda x: (-counts[x], rest.index(x))):
        for g in groups:
            if counts[g[0]] != counts[f]:
                continue
            q = ' AND '.join([base] + [f'{x} {ANY}' for x in g + [f]])
            name = '+'.join(re.sub(r'\W+', '_', x) for x in g + [f])
            d, _ = await fetch(os.path.join(pdir, name + '.json'), args_for(q, limit=1), log)
            combos[' + '.join(g + [f])] = d['total_matches']
            if d['total_matches'] == counts[f]:
                g.append(f)
                break
        else:
            groups.append([f])
    out = {'counts': counts, 'on_column_row': on_row, 'combined_counts': combos, 'groups': groups,
           'bands': [[i, lo, hi] for i, lo, hi in bands(cfg)]}
    scr_tool.save(out, gp)
    log(f'columns ok ({len(cfg["columns"])}); query fields on the column row: {on_row}; counts {counts}; groups {groups}')
    return groups


def build(sdir=None):
    """<run>/universe.csv from every saved page in <run>/screens/: one row per symbol with hits (the T screens it matched),
    in_sweep (in a B band) and every field found (Q pages only add fields). Returns (warnings, summary): a query whose
    saved companies don't add up to its total, and columns of screens.json never returned."""
    base = run_dir()
    sdir = sdir or os.path.join(base, 'screens')
    cfg = json.load(open(os.path.join('workflow', 'screens.json'), encoding='utf-8'))
    rows, hits, swept, totals, warn = {}, {}, set(), {}, []
    for fn in sorted(glob.glob(os.path.join(sdir, '*_p*.json'))):
        sid = re.sub(r'_(asc|desc)$', '', re.match(r'(.+)_p\d+\.json$', os.path.basename(fn)).group(1))
        data = json.load(open(fn, encoding='utf-8'))['data']
        t = totals.setdefault(sid, [data.get('total_matches'), set()])
        for r in data.get('results', []):
            t[1].add(r['symbol'])  # asc and desc pages overlap: count distinct companies
            row = rows.setdefault(r['symbol'], {'sym': r['symbol'], 'name': r.get('name') or '', 'screener_id': r.get('company_id')})
            row.update({k: v for k, v in (r.get('fundamentals') or {}).items() if v is not None})
            if sid.startswith('B'):
                swept.add(r['symbol'])
            elif sid.startswith('T'):
                hits.setdefault(r['symbol'], set()).add(sid)
    for sid, (total, got) in sorted(totals.items()):
        if total is not None and len(got) != total:
            warn.append(f'{sid}: {len(got)} companies saved of {total}: a page is missing')
    missing_cols = [c for c in cfg['columns'] + cfg.get('query_fields', []) if not any(c in r for r in rows.values())]
    if missing_cols:
        warn.append(f'columns never returned (check the account column set): {missing_cols}')
    keys = ['sym', 'name', 'screener_id', 'hits', 'in_sweep']
    for r in rows.values():
        keys += [k for k in r if k not in keys]
    order = lambda x: sorted(x, key=lambda y: (len(y), y))
    for s_, r in rows.items():
        r['hits'] = '+'.join(order(hits.get(s_, ())))
        r['in_sweep'] = s_ in swept
    W.write_csv(os.path.join(base, 'universe.csv'), keys, [r for _, r in sorted(rows.items())])
    return warn, f'companies {len(rows)} screen hits {len(hits)} in sweep {len(swept)}'


def check_build(final, done):
    """build(); stops on warnings about the queries finished so far (done), and on the columns warning only after the
    last query (later queries' pages may still be missing from an interrupted run)."""
    warn, summ = build()
    def counts(w):
        m = re.match(r'(\S+): \d+ companies saved', w)
        return (m.group(1) in done) if m else (final or 'columns never returned' not in w)
    bad = [w for w in warn if counts(w)]
    if bad:
        raise Stop('universe check: ' + ' | '.join(bad))
    return summ


async def query(qid, q, sdir, log, summary):
    d, new = await fetch(os.path.join(sdir, f'{qid}_desc_p01.json'), args_for(q), log)
    t = d['total_matches']
    files = [(f'{qid}_desc_p{p:02d}.json', 'desc', p) for p in range(2, max(1, t // LIMIT) + 1)]
    if t > LIMIT and t % LIMIT:
        files.append((f'{qid}_asc_p01.json', 'asc', 1))
    fetched = int(new)
    for fn, order, p in files:
        _, new = await fetch(os.path.join(sdir, fn), args_for(q, order, p), log)
        fetched += new
    syms = set()
    for fn in glob.glob(os.path.join(sdir, f'{qid}_*_p*.json')):
        syms |= {r['symbol'] for r in (valid(fn) or {}).get('data', {}).get('results', [])}
    summary.append((qid, t, len(files) + 1, len(syms)))
    log(f'{qid}: total {t}, pages {len(files) + 1} ({fetched} fetched now), companies saved {len(syms)}')


async def cmd_run(a):
    scr_tool.prepare(login=True)
    log = lambda m: print(m, flush=True)
    cfg = json.load(open(os.path.join('workflow', 'screens.json'), encoding='utf-8'))
    sdir = os.path.join(run_dir(), 'screens')
    os.makedirs(sdir, exist_ok=True)
    summary = []
    try:
        groups = await probe(cfg, sdir, log)
        if a.probe_only:
            return 0
        qs = [(sid, s['query']) for sid, s in cfg['screens'].items()]
        qs += [(bid, band_query(cfg['base'], lo, hi)) for bid, lo, hi in bands(cfg)]
        for gi, g in enumerate(groups, 1):
            fq = ' AND '.join(f'{f} {ANY}' for f in g)
            qs += [(f'Q{gi}{bid}', band_query(f"{cfg['base']} AND {fq}", lo, hi)) for bid, lo, hi in bands(cfg)]
        only = set(a.only.split(',')) if a.only else None
        if only and only - {q for q, _ in qs}:
            raise Stop(f'unknown IDs in --only: {sorted(only - {q for q, _ in qs})}')
        todo = [x for x in qs if not only or x[0] in only]
        done = set()
        for i, (qid, q) in enumerate(todo):
            await query(qid, q, sdir, log, summary)
            done.add(qid)
            last = check_build(final=(i == len(todo) - 1 and not only), done=done)
        log(f'universe: {last}')
    except Stop as e:
        print(f'STOPPED: {e}', flush=True)
        code = 3 if str(e).startswith(('COLUMNS MISSING', 'universe check')) else 2
        return code
    finally:
        if summary:
            print('\n| ID | total | pages | companies saved |\n|---|---|---|---|')
            for qid, t, p, n in summary:
                print(f'| {qid} | {t} | {p} | {n} |')
    return 0


def cmd_build(a):
    warn, summ = build()
    for w in warn:
        print('WARNING', w)
    print(summ)
    return 1 if warn else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True, help='the mode; <mode> --help for its own help')
    p = sp.add_parser('run', help='probes, screens and sweeps (uvx, logged in)', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--only', help='comma-separated query IDs (T3,B05,Q1B02)')
    p.add_argument('--probe-only', action='store_true', help='stop after the column probe, query-field probes and groups')
    sp.add_parser('build', help='universe.csv from the saved pages', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a = ap.parse_args()
    return asyncio.run(cmd_run(a)) if a.cmd == 'run' else cmd_build(a)


if __name__ == '__main__':
    sys.exit(main())
