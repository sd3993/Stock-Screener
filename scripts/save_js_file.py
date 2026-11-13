"""Large browser results are saved by the harness as [{type, text}]; the text is the JS value
(JSON-encoded) followed by "(captured at origin ...)". Decode it and write the inner JSON object.

usage: save_js_file.py <saved page-script result file> <out.json>
"""
import json, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding='utf-8'))
text = ''.join(x.get('text', '') for x in d) if isinstance(d, list) else str(d)
body = text.split('\n\n(captured at origin')[0].strip()
v = json.loads(body)
if isinstance(v, str):
    v = json.loads(v)
json.dump(v, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
tag = next((v[k] for k in v if k.isupper()), None)
print('saved', out, 'tag', tag, 'records', v.get('n'), 'missing', [r['s'] for r in v.get('d', []) if r.get('missing')])
