import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt
# Saves the latest MCP tool result to a file, so a helper's Tapetide answers are cached without re-typing them.
# Searches this project's transcripts (sessions and their subagents) for the newest tool_result that contains
# --marker; --tag (a unique word from the helper's brief) restricts the search to that helper's own transcript.
# Run it right after the tool call, so "latest" is that call. Logs the call in data/calls.csv.
#   screens:  --marker total_pages --out <run>/screens/T1_p01.json --page 1 --tag <tag>
#   cache:    --marker <a word in the answer> --out data/companies/<SYM>/api/<name>.json --wrap <tool name> --sym <SYM> --tag <tag>
p = argparse.ArgumentParser()
p.add_argument('--marker', required=True)
p.add_argument('--out', required=True)
p.add_argument('--tag')
p.add_argument('--page', help='expected page number (screens)')
p.add_argument('--wrap', help='MCP tool name: save inside the cache envelope used by tt.py')
p.add_argument('--sym', default='')
a = p.parse_args()

proj = os.environ.get('CC_PROJECT_DIR', os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                      'C--Users-sd391-OneDrive-Documents-Projects-Stock-Screener'))
files = glob.glob(os.path.join(proj, '*.jsonl')) + glob.glob(os.path.join(proj, '*', 'subagents', '**', '*.jsonl'), recursive=True)
files = sorted(files, key=os.path.getmtime, reverse=True)[:40]
if a.tag:
    files = [f for f in files if a.tag in open(f, encoding='utf-8', errors='replace').read(400000)]
if not files:
    sys.exit('no transcript found under ' + proj + (' with tag ' + a.tag if a.tag else ''))
src = files[0]
last = None
for line in open(src, encoding='utf-8', errors='replace'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    content = (o.get('message') or {}).get('content')
    if not isinstance(content, list):
        continue
    for c in content:
        if not isinstance(c, dict) or c.get('type') != 'tool_result':
            continue
        cc = c.get('content')
        text = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
        if a.marker in text and text.lstrip().startswith(('{', '[')):
            last = text
if last is None:
    sys.exit('no tool_result containing the marker in ' + src)
d = json.loads(last)  # fails loudly if the result was cut off
if a.page and isinstance(d, dict) and str(d.get('page')) != a.page:
    sys.exit(f"latest result is page {d.get('page')}, expected {a.page}: the latest call probably failed; nothing saved")
if isinstance(d, dict) and (d.get('meta') or {}).get('truncated'):
    sys.exit('the result was cut to fit the tool-result limit: narrow the request (smaller limit or a section) and call again; nothing saved')
os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
if a.wrap:
    tt.save(a.out, a.wrap, None, d, via='mcp')
else:
    open(a.out, 'w', encoding='utf-8').write(last)
tt.log_call('mcp', a.wrap or 'screen_stocks', a.sym, None, 200)
print('saved', a.out, 'from', os.path.basename(src), *(('page', d.get('page'), 'of', d.get('total_pages')) if isinstance(d, dict) and 'page' in d else ()))
