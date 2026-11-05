import json, sys, glob, os, re
# usage: save_last_js.py <marker> <out_file> <agent_tag> <i> <j>
# Saves the last browser javascript_tool result whose text contains <marker> from the subagent
# transcript tagged <agent_tag>. The JS returns JSON.stringify({<marker>:[i,j], ...}); the range is
# checked so a failed call can't save an older result under a new name.
marker, out, tag, i, j = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
# The session is CC_SESSION_DIR if set, else the most recently written transcript in this project's Claude folder.
proj = os.path.join(os.path.expanduser('~'), '.claude', 'projects', re.sub(r'[^A-Za-z0-9]', '-', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sess = os.environ.get('CC_SESSION_DIR') or max(glob.glob(os.path.join(proj, '*.jsonl')), key=os.path.getmtime)[:-6]
if tag == 'MAIN':  # the main session's own transcript
    files = [sess + '.jsonl']
else:
    files = [f for f in glob.glob(os.path.join(sess, 'subagents', '**', '*.jsonl'), recursive=True)
             if tag in open(f, encoding='utf-8').read(200000)]
if not files:
    sys.exit('no subagent transcript with tag ' + tag)
src = max(files, key=os.path.getmtime)
last = None
for line in open(src, encoding='utf-8'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    content = (o.get('message') or {}).get('content')
    if not isinstance(content, list):
        continue
    for c in content:
        if c.get('type') != 'tool_result':
            continue
        cc = c.get('content')
        text = ''.join(x.get('text', '') for x in cc if isinstance(x, dict)) if isinstance(cc, list) else str(cc)
        if marker in text and '(captured at origin' in text:
            last = text
if last is None:
    sys.exit('no javascript result with marker ' + marker)
body = last.split('\n\n(captured at origin')[0].strip()
v = json.loads(body)
if isinstance(v, str):
    v = json.loads(v)
if v.get(marker) != [i, j]:
    sys.exit(f'last result covers {v.get(marker)}, expected {[i, j]}: the latest call probably failed; nothing saved')
json.dump(v, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
print('saved', out, 'stocks', v.get('n'), 'errors', [d['s'] for d in v.get('d', []) if 'err' in d or 'err2' in d])
