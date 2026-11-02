import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt
from config import run_dir
# P2 with an API token: runs every screen and dump in process/screens.json through the REST screener, 50 rows a page,
# saving each page as <run>/screens/<ID>_pNN.json. Resumes: pages already saved are skipped (a screen's cursor chain
# is replayed from page 1 only if an earlier page is missing). Stops cleanly when the daily quota runs out.
# The REST screener returns every queried ratio in ratio_values, so the dumps are tried as one combined query
# (D_ALL) first; if page 1 lacks any field, it falls back to the two-field dumps.
cfg = json.load(open('process/screens.json', encoding='utf-8'))
out = os.path.join(run_dir(), 'screens')
os.makedirs(out, exist_ok=True)

def run(sid, query, sort='Market Capitalization', order='desc'):
    params = {'query': query, 'sort': sort, 'order': order, 'limit': 50}
    page, total = 1, None
    while True:
        fn = os.path.join(out, f'{sid}_p{page:02d}.json')
        if os.path.exists(fn):
            body = json.load(open(fn, encoding='utf-8'))
        else:
            body = tt.request('/v1/screens/fundamental', params, symbol='_screen:' + sid)
            json.dump(body, open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
        meta = body.get('meta') or {}
        total = meta.get('total_matches', total)
        if not meta.get('next_cursor'):
            break
        params['cursor'] = meta['next_cursor']
        page += 1
    print(f'{sid}: {total} matches, {page} pages')
    return body

try:
    for sid, s in cfg['screens'].items():
        run(sid, s['query'], s.get('sort', 'Market Capitalization'), s.get('order', 'desc'))
    fields = [f for d in cfg['dumps'].values() for f in d['fields']]
    q = cfg['dump_base'] + ''.join(f' AND {f} > -9999999' for f in fields)
    first = os.path.join(out, 'D_ALL_p01.json')
    if not os.path.exists(first) and os.path.exists(os.path.join(out, 'D1_p01.json')):
        combined_ok = False  # an earlier run already fell back to the two-field dumps
    else:
        if not os.path.exists(first):
            body = tt.request('/v1/screens/fundamental', {'query': q, 'limit': 50, 'sort': 'Market Capitalization', 'order': 'desc'}, symbol='_screen:D_ALL')
            rv = ((body.get('data') or [{}])[0]).get('ratio_values') or {}
            combined_ok = all(f in rv for f in fields)
            if combined_ok:
                json.dump(body, open(first, 'w', encoding='utf-8'), ensure_ascii=False)
            else:
                print('combined dump lacks', [f for f in fields if f not in rv], '-> two-field dumps')
        else:
            combined_ok = True
    if combined_ok:
        run('D_ALL', q)
    else:
        for did, d in cfg['dumps'].items():
            run(did, cfg['dump_base'] + ''.join(f' AND {f} > -9999999' for f in d['fields']))
    print('ALL DONE')
except tt.QuotaExceeded as e:
    print('QUOTA EXCEEDED, stopped; re-run after the reset to resume.', e)
    sys.exit(3)
