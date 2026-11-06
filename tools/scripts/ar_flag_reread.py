#!/usr/bin/env python
# P6.0 follow-up: turns ar_parsed_flags.csv into rows for helpers to re-read, in the shape of p7_group.csv plus `flags`.
#   python -I tools/scripts/ar_flag_reread.py <run folder> [--size 25]
# Takes values that reach the features ([used]). A report flagged only by the weak checks (page_earlier, unit_mismatch,
# cross_value, chart_value: high false positives or nothing a re-read would settle alone) is left out. Reports still in the
# helper queue are left out too, since a helper reads them anyway. Writes <run>/p7/flag_reread.csv, one group number per --size.
import argparse, collections, csv, glob, json, os, re

WEAK = {'page_earlier', 'unit_mismatch', 'cross_value', 'chart_value'}
ap = argparse.ArgumentParser()
ap.add_argument('run')
ap.add_argument('--size', type=int, default=25)
a = ap.parse_args()

flags = collections.defaultdict(list)
for r in csv.DictReader(open(f'{a.run}/ar_parsed_flags.csv', encoding='utf-8')):
    if r['detail'].startswith('[used]'):
        flags[(r['sym'], r['fy'])].append(r)
queued = {(r['sym'], 'FY' + r['fy'][-2:]) for r in csv.DictReader(open(f'{a.run}/ar_helper_queue.csv', encoding='utf-8'))}

rows, no_file = [], []
for (sym, fy), fl in sorted(flags.items()):
    if (sym, fy) in queued or not {x['check'] for x in fl} - WEAK:
        continue
    hits = glob.glob(f'data/companies/{sym}/{fy}Q*/ar_{fy}.json')
    if not hits:
        no_file.append(f'{sym} {fy}')
        continue
    jf = hits[0].replace('\\', '/')
    url = json.load(open(jf, encoding='utf-8')).get('url', '')
    asked = collections.defaultdict(set)
    for x in fl:
        if x['year'] and x['basis'] in ('standalone', 'consolidated') and re.fullmatch(r'[a-z_]+', x['field']):
            asked[(x['basis'][0], x['year'])].add(x['field'])
    fields = '; '.join(f"{b}:{y}:{'|'.join(sorted(fs))}" for (b, y), fs in sorted(asked.items()))
    text = '; '.join(sorted({f"{x['check']} {x['basis'][:1]}:{x['year']}:{x['field']} {x['detail'][7:90]}" for x in fl if x['check'] not in WEAK}))
    rows.append(dict(group=len(rows) // a.size + 1, sym=sym, fy='20' + fy[-2:], fields=fields, page_text=jf[:-5] + '_pages.txt',
                     json=jf, url=url, helper_file=jf[:-5] + '_helper.json', flags=text))
out = f'{a.run}/p7/flag_reread.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['group', 'sym', 'fy', 'fields', 'page_text', 'json', 'url', 'helper_file', 'flags'])
    w.writeheader()
    w.writerows(rows)
print(f'{len(rows)} reports, {len({r["sym"] for r in rows})} companies, {rows[-1]["group"] if rows else 0} groups -> {out}; no json: {no_file}; no url: {sum(not r["url"] for r in rows)}')
print(collections.Counter(c for r in rows for c in {x.split()[0] for x in r['flags'].split('; ') if x}).most_common())
