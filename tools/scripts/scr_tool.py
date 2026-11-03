import asyncio, datetime as dt, inspect, json, os, sys
# Calls any screener tool (the functions the screener MCP exposed, e.g. screen_stocks, get_peer_comparison) through the
# screener-mcp library and saves the answer to a file, never into context. Replaces the MCP plus scr_save.py.
#   uvx --from screener-mcp==0.5.0 python tools/scripts/scr_tool.py <tool> '<args as JSON>' <out.json> [--login]
#   e.g. scr_tool.py screen_stocks '{"query": "Market Capitalization > 250", "limit": 200, "page": 1}' runs/.../B01_p01.json --login
# Screens need --login (the screener login from the environment; tools/tools.md); company tools work without it.
# Writes {fetched_at (IST), via: "screener-lib", tool, args, warnings, data}, the same envelope as scr_save.py, and prints
# the page and totals for screens. Exits non-zero on an error answer (the file is still written, with the reason).
os.environ.setdefault('SCREENER_MIN_INTERVAL', '1.2')
if '--login' not in sys.argv:
    for k in ('SCREENER_USERNAME', 'SCREENER_PASSWORD'):
        os.environ.pop(k, None)
import screener_mcp.server as srv  # the MCP's own tool functions, with the same names, arguments and answers

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
a = [x for x in sys.argv[1:] if x != '--login']
tool, args, out = a[0], json.loads(a[1]), a[2]

def find(name):
    fn = getattr(srv, name, None)
    if not inspect.iscoroutinefunction(fn):
        sys.exit(f'no screener tool named {name}')
    return fn

async def main():
    r = await find(tool)(**args)  # the MCP envelope: {status, partial, warnings, data, reason?}
    data, ok = r.get('data'), r.get('status') == 'ok'
    warns = list(r.get('warnings') or []) + ([r['reason']] if r.get('reason') else [])
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump({'fetched_at': dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'screener-lib', 'tool': tool,
               'args': args, 'warnings': warns, 'partial': r.get('partial'), 'data': data},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if not ok:
        sys.exit(f'{out}: {r.get("status")}: {(warns or ["no reason given"])[-1][:200]}')
    if isinstance(data, dict) and 'total_matches' in data:
        print(f'{out}: page {args.get("page", 1)}, {len(data.get("results", []))} rows of {data["total_matches"]}'
              + (' (PARTIAL)' if r.get('partial') else ''))
    else:
        print(f'{out}: saved' + (' (PARTIAL)' if r.get('partial') else '') + (f'; warnings: {warns}' if warns else ''))

asyncio.run(main())
