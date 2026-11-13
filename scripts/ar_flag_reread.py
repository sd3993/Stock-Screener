#!/usr/bin/env python
"""Annual-report statements follow-up (workflow/ar_statements.md): turns ar_parsed_flags.csv into rows for subagents to re-read.

  python -I scripts/ar_flag_reread.py [--dir data/playbook] [--size 25]

Works in the playbook base data folder: --dir, else the PLAYBOOK_DATA environment variable, else data/playbook.
Reads ar_parsed_flags.csv and ar_helper_queue.csv there. Takes values that reach the features ([used]). A report flagged
only by the weak checks (page_earlier, unit_mismatch, cross_value, chart_value: high false positives or nothing a re-read
would settle alone) is left out. Reports still in the subagent queue are left out too, since a subagent reads them anyway.
Writes flag_reread.csv in the same folder, one group number per --size: the columns of ar_helper_queue.csv (group, sym,
fy, fields, page_text, json, url, helper_file) plus flags (the strong checks that flagged the report).
Prints the report, company and group counts, reports with no parsed json, and the flag counts per check.
"""
import argparse, collections, csv, glob, json, os, re

WEAK = {'page_earlier', 'unit_mismatch', 'cross_value', 'chart_value'}
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', default=None, help='playbook base data folder (default: PLAYBOOK_DATA, else data/playbook)')
ap.add_argument('--size', type=int, default=25, help='reports per group (default: %(default)s)')
a = ap.parse_args()
D = a.dir or os.environ.get('PLAYBOOK_DATA') or os.path.join('data', 'playbook')  # the playbook base data folder (config.playbook_dir)

flags = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, 'ar_parsed_flags.csv'), encoding='utf-8')):
    if r['detail'].startswith('[used]'):
        flags[(r['sym'], r['fy'])].append(r)
queued = {(r['sym'], 'FY' + r['fy'][-2:]) for r in csv.DictReader(open(os.path.join(D, 'ar_helper_queue.csv'), encoding='utf-8'))}

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
out = os.path.join(D, 'flag_reread.csv')
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['group', 'sym', 'fy', 'fields', 'page_text', 'json', 'url', 'helper_file', 'flags'])
    w.writeheader()
    w.writerows(rows)
print(f'{len(rows)} reports, {len({r["sym"] for r in rows})} companies, {rows[-1]["group"] if rows else 0} groups -> {out}; no json: {no_file}; no url: {sum(not r["url"] for r in rows)}')
print(collections.Counter(c for r in rows for c in {x.split()[0] for x in r['flags'].split('; ') if x}).most_common())
