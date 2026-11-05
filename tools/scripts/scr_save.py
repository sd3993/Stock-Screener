import argparse, datetime as dt, glob, json, os, sys
# Saves a screener MCP answer to a file, so it is cached without re-typing it (and without reading it into context).
# Only for old answers in transcripts: the MCP was removed on 3 Nov 2026; new calls go through scr_tool.py.
#   --file PATH      an oversized answer the app already saved (the path printed in the tool's "exceeds maximum
#                    allowed tokens" message); nothing enters context.
#   --marker WORD    otherwise, the newest tool result containing WORD in this project's transcripts (sessions and
#                    their subagents); --tag (a unique word from the helper's brief) restricts it to that helper.
# Run it right after the tool call. Writes {fetched_at (IST), via: "screener", tool, args, data}; fails loudly on a
# cut-off or error answer. Prints the page and totals for screens.
#   python tools/scripts/scr_save.py --tool screen_stocks --args '{"query": "...", "page": 1}' --out <run>/screens/D_b01_p01.json --file <path>
#   python tools/scripts/scr_save.py --tool get_financials --args '{"symbol": "TCS", "statement": "cash_flow"}' --out data/companies/TCS/scr/cash_flow.json --marker cash_flow --tag <tag>
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
p = argparse.ArgumentParser()
p.add_argument('--tool', required=True)
p.add_argument('--args', default='{}', help='the call arguments, as JSON (recorded with the answer)')
p.add_argument('--out', required=True)
p.add_argument('--file')
p.add_argument('--marker')
p.add_argument('--tag')
a = p.parse_args()

def from_transcript(marker, tag):
    proj = os.environ.get('CC_PROJECT_DIR', os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                          'C--Users-sd391-Projects-Stock-Screener'))
    files = glob.glob(os.path.join(proj, '*.jsonl')) + glob.glob(os.path.join(proj, '*', 'subagents', '**', '*.jsonl'), recursive=True)
    files = sorted(files, key=os.path.getmtime, reverse=True)[:40]
    if tag:
        files = [f for f in files if tag in open(f, encoding='utf-8', errors='replace').read(400000)]
    if not files:
        sys.exit('no transcript found under ' + proj)
    last = None
    for line in open(files[0], encoding='utf-8', errors='replace'):
        try:
            content = (json.loads(line).get('message') or {}).get('content')
        except Exception:
            continue
        for c in content if isinstance(content, list) else []:
            if isinstance(c, dict) and c.get('type') == 'tool_result':
                cc = c.get('content')
                text = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
                if marker in text and text.lstrip().startswith('{'):
                    last = text
    if last is None:
        sys.exit(f'no tool result containing {marker!r} in {os.path.basename(files[0])}')
    return last

if a.file:
    text = open(a.file, encoding='utf-8').read()
elif a.marker:
    text = from_transcript(a.marker, a.tag)
else:
    sys.exit('give --file or --marker')
d = json.loads(text)  # a cut-off answer fails here
if d.get('status') != 'ok':
    sys.exit(f"answer status {d.get('status')}: {str(d)[:300]}; nothing saved")
args = json.loads(a.args)
data = d.get('data') or {}
if 'page' in args and str(data.get('page')) != str(args['page']):
    sys.exit(f"answer is page {data.get('page')}, expected {args['page']}: the latest call probably failed; nothing saved")
os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
env = {'fetched_at': dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 'via': 'screener', 'tool': a.tool, 'args': args,
       'warnings': d.get('warnings'), 'partial': d.get('partial'), 'data': data}
json.dump(env, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
extra = f" page {data.get('page')}, {data.get('showing')} rows of {data.get('total_matches')}" if 'total_matches' in data else ''
print('saved', a.out + extra, '(partial!)' if d.get('partial') else '')
