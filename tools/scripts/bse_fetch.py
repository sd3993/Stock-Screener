import datetime as dt, json, os, sys
# BSE APIs for companies NSE doesn't cover, through the browser pane. BSE's API refuses scripts (bot protection;
# working around it isn't allowed) and the pane can't post to a local receiver, so a real tab on www.bseindia.com makes
# the calls, as BSE's own site does, and its answers reach disk through one large javascript_tool result, which the app
# saves to a file (results over MAX_MCP_OUTPUT_TOKENS are saved, never shown; the padding below forces that).
#   1. python tools/scripts/bse_fetch.py job SYM [SYM ...] [--items pledge,shp,results,actions,announcements] [--days 365]
#      prints the job; a numeric SYM is the BSE scrip code (screener names BSE-only companies by it). About 20 a batch.
#   2. browser pane, a tab on https://www.bseindia.com/: once per tab, run the text of tools/scripts/bse_fetch.js
#      (javascript_tool); then run  __bseRun(<job>)
#   3. poll  JSON.stringify({d: __bse.done, f: __bse.finished, e: __bse.errors.length})  until f is true
#      (about 1 s per request; 5 items for one company take about 10 s, more with long announcement lists)
#   4. collect  JSON.stringify({BSEOUT: __bse.job.syms, out: __bse.out, errors: __bse.errors, pad: ' '.repeat(16000)})
#      and pass the saved result file to:  python tools/scripts/bse_fetch.py save <tool-results file>
# Writes data/companies/<SYM>/bse/<item>.json as {fetched_at (IST), via: "bse-browser", url, data} (or error).
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
ITEMS = ['pledge', 'shp', 'results', 'actions', 'announcements']
args = sys.argv[1:]
def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default

if args[:1] == ['job'] and len(args) > 1:
    items = opt('--items', ','.join(ITEMS)).split(',')
    days = int(opt('--days', '365'))
    if any(i not in ITEMS for i in items):
        sys.exit('items: ' + ','.join(ITEMS))
    today = dt.datetime.now(IST).date()
    print(json.dumps({'syms': args[1:], 'items': items, 'from': (today - dt.timedelta(days=days)).strftime('%Y%m%d'),
                      'to': today.strftime('%Y%m%d')}, separators=(',', ':')))
elif args[:1] == ['save'] and len(args) == 2:
    d = json.load(open(args[1], encoding='utf-8'))
    text = ''.join(x.get('text', '') for x in d) if isinstance(d, list) else str(d)
    v = json.loads(text.split('\n\n(captured at origin')[0].strip())
    if isinstance(v, str):
        v = json.loads(v)
    if 'BSEOUT' not in v:
        sys.exit('not a bse_fetch result (no BSEOUT): nothing saved')
    now = dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
    for sym in v['BSEOUT']:
        o = v['out'].get(sym)
        if not o:
            print(sym, 'not fetched (tab stopped early?)'); continue
        if not o.get('code'):
            print(sym, 'not on BSE list'); continue
        out_dir = os.path.join('data', 'companies', sym, 'bse'); os.makedirs(out_dir, exist_ok=True)
        got = []
        for item, r in o.items():
            if item == 'code':
                continue
            env = {'fetched_at': now, 'via': 'bse-browser', 'url': r.get('url'), 'data': r.get('data')}
            if 'error' in r:
                env['error'] = r['error']
            json.dump(env, open(os.path.join(out_dir, item + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            got.append(item + ('(error)' if 'error' in r else ''))
        print(sym, o['code'], ' '.join(got))
    if v.get('errors'):
        print('errors:', '; '.join(v['errors']))
else:
    sys.exit('usage: bse_fetch.py job SYM [SYM ...] [--items ...] [--days 365]  |  bse_fetch.py save <tool-results file>')
