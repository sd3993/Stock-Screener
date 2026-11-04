# Builds the next business-type tagging batch for the multibagger study (S2): rows from needs_next.csv (written by
# mb_sample.py --finalize) not in any earlier batch (input or output), for companies already fetched by the S2/S3 run (scr/documents.json;
# the industry-label fetch writes only overview.json),
# up to 25 companies, in needs_next order. Writes business_types/batch_<N>_input.csv, N = next free number.
# Usage (project root): python tools/scripts/mb_tag_batch.py runs/historical/<date> [--size 25]
import csv, glob, os, re, sys

run = sys.argv[1]
size = int(sys.argv[sys.argv.index('--size') + 1]) if '--size' in sys.argv else 25
bt = os.path.join(run, 'business_types')
done, nums = set(), [0]
for f in glob.glob(os.path.join(bt, 'batch_*.csv')):
    m = re.search(r'batch_(\d+)(_input)?\.csv$', f)
    if not m:
        continue
    nums.append(int(m.group(1)))
    with open(f, encoding='utf-8') as fh:  # inputs too: a batch still running (or cut off, to re-run) keeps its rows
        done |= {(x['sym'], x['as_of']) for x in csv.DictReader(fh)}
with open(os.path.join(run, 'needs_next.csv'), encoding='utf-8') as fh:
    rows = [x for x in csv.DictReader(fh) if (x['sym'], x['as_of']) not in done]
fetched = lambda s: os.path.exists(os.path.join('data', 'companies', s, 'scr', 'documents.json'))
syms = list(dict.fromkeys(x['sym'] for x in rows))
ready = [s for s in syms if fetched(s)][:size]
out = list({(x['sym'], x['as_of']): {'sym': x['sym'], 'as_of': x['as_of'], 'groups': x['groups']}
             for x in rows if x['sym'] in ready}.values())
n = max(nums) + 1
if not out:
    print(f'nothing to tag: {len(syms)} companies left, none fetched yet' if syms else 'nothing left to tag')
    sys.exit(1)
path = os.path.join(bt, f'batch_{n}_input.csv')
with open(path, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['sym', 'as_of', 'groups'])
    w.writeheader()
    w.writerows(out)
print(f'{path}: {len(ready)} companies, {len(out)} rows; left after this: {len(syms) - len(ready)} '
      f'({sum(1 for s in syms if not fetched(s))} not fetched yet)')
