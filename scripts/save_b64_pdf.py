"""Decodes a PDF fetched in the browser as base64 (javascript result saved by the harness as [{type, text}])
into <out.pdf>, extracts its text next to it and prints the first lines.

usage: python -I scripts/save_b64_pdf.py <tool-results file> <out.pdf> [lines]
"""
import base64, json, os, subprocess, sys
if __name__ == '__main__' and {'-h', '--help'} & set(sys.argv[1:]):
    print(__doc__)
    sys.exit(0)
src, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
d = json.load(open(src, encoding='utf-8'))
t = ''.join(x.get('text', '') for x in d) if isinstance(d, list) else str(d)
v = json.loads(t.split('\n\n(captured at origin')[0].strip())
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'wb').write(base64.b64decode(v['b64']))
txt = out[:-4] + '.txt'
subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf_text.py'), out, '1', '60', txt], capture_output=True)
sys.stdout.reconfigure(encoding='utf-8')
print('bytes', v.get('n'), '->', out)
if os.path.exists(txt):
    lines = [l.strip() for l in open(txt, encoding='utf-8', errors='replace') if l.strip()]
    print('\n'.join(lines[:n]))
