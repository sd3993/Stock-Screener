# Cut each report in ar_helper_queue.csv down to the pages reading helpers need: writes ar_FY<yy>_stmt.txt beside its ar_FY<yy>_pages.txt,
# holding the pages the parser used (bases.*.pages in ar_FY<yy>.json) and every page showing cash from operating activities.
# Helpers open it first and go to the full pages file only if a statement is missing.
#   python -I tools/scripts/ar_trim.py [--dir data/playbook]
# A report with no page identified gets no _stmt.txt, so its helper reads the full file. Safe to re-run.
import argparse, csv, glob, json, os, re

CF = re.compile(r'operating\s+activit', re.I)
a = argparse.ArgumentParser()
a.add_argument('--dir', default=None)
a = a.parse_args()
D = a.dir or os.environ.get('PLAYBOOK_DATA') or os.path.join('data', 'playbook')  # the playbook base data folder (config.playbook_dir)


def used_pages(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'pages':
                for y in (v.values() if isinstance(v, dict) else v if isinstance(v, list) else [v]):
                    if y is not None:
                        out.add(str(y))
            else:
                used_pages(v, out)
    return out


n = cut = none = chars = kept = 0
for r in csv.DictReader(open(os.path.join(D, 'ar_helper_queue.csv'), encoding='utf-8')):
    pf, jf = r['page_text'], r['json']
    if not (os.path.exists(pf) and os.path.exists(jf)):
        none += 1
        continue
    pgs = used_pages(json.load(open(jf, encoding='utf-8')).get('bases') or {}, set())
    t = open(pf, encoding='utf-8', errors='replace').read()
    n += 1
    chars += len(t)
    keep = []
    found = False
    for part in re.split(r'(?==== page )', t):
        m = re.match(r'=== page (\S+)', part)
        if not m:
            continue
        hit = m.group(1) in pgs or re.sub(r'\D', '', m.group(1)) in pgs
        found = found or hit
        if hit or CF.search(part):
            keep.append(part)
    out = pf.replace('_pages.txt', '_stmt.txt')
    if not found:
        none += 1
        if os.path.exists(out):
            os.remove(out)
        continue
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(''.join(keep))
    os.replace(tmp, out)
    cut += 1
    kept += sum(map(len, keep))
print(f'{cut} reports trimmed, {none} left to the full file; {n} read, {chars:,} chars -> trimmed ones hold {kept:,}')
