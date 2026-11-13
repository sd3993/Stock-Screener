"""Calls any screener tool (the functions the screener MCP exposed, e.g. screen_stocks, get_peer_comparison) through the
screener-mcp library and saves the answer to a file, never into context. Replaces the MCP.
  uvx --from screener-mcp==0.5.0 python scripts/scr_tool.py <tool> '<args as JSON>' <out.json> [--login]
  e.g. scr_tool.py screen_stocks '{"query": "Market Capitalization > 250", "limit": 200, "page": 1}' runs/.../B01_p01.json --login
Screens need --login (the screener login from the environment; sources/screener.md); company tools work without it. If screener.in can't be reached: principles/access_rules.md.
Writes {fetched_at (IST), via: "screener-lib", tool, args, warnings, data} and prints
the page and totals for screens. Exits non-zero on an error answer (the file is still written, with the reason).
Other scripts reuse call() and save() (screens.py); they import this file without running it.
"""
import asyncio, datetime as dt, inspect, json, os, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def prepare(login):
    """Public mode unless login: drop the screener login from the environment before the library loads."""
    os.environ.setdefault('SCREENER_MIN_INTERVAL', '1.2')
    if not login:
        for k in ('SCREENER_USERNAME', 'SCREENER_PASSWORD'):
            os.environ.pop(k, None)


async def call(tool, args):
    """The tool's answer as the saved envelope, plus ok (status ok and not partial-with-error)."""
    import screener_mcp.server as srv  # the MCP's own tool functions, with the same names, arguments and answers
    fn = getattr(srv, tool, None)
    if not inspect.iscoroutinefunction(fn):
        raise SystemExit(f'no screener tool named {tool}')
    r = await fn(**args)  # the MCP envelope: {status, partial, warnings, data, reason?}
    warns = list(r.get('warnings') or []) + ([r['reason']] if r.get('reason') else [])
    env = {'fetched_at': dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'screener-lib', 'tool': tool,
           'args': args, 'warnings': warns, 'partial': r.get('partial'), 'data': r.get('data')}
    return env, r.get('status') == 'ok', r.get('status')


def save(env, out):
    """Write the envelope (temp file, then rename, so a page file is never half-written)."""
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(env, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, out)


async def main():
    a = [x for x in sys.argv[1:] if x != '--login']
    tool, args, out = a[0], json.loads(a[1]), a[2]
    env, ok, status = await call(tool, args)
    save(env, out)
    data, warns = env['data'], env['warnings']
    if not ok:
        sys.exit(f'{out}: {status}: {(warns or ["no reason given"])[-1][:200]}')
    if isinstance(data, dict) and 'total_matches' in data:
        print(f'{out}: page {args.get("page", 1)}, {len(data.get("results", []))} rows of {data["total_matches"]}'
              + (' (PARTIAL)' if env.get('partial') else ''))
    else:
        print(f'{out}: saved' + (' (PARTIAL)' if env.get('partial') else '') + (f'; warnings: {warns}' if warns else ''))


if __name__ == '__main__':
    prepare('--login' in sys.argv)
    asyncio.run(main())
