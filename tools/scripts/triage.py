import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import run_dir
# S3: scores every company in <run>/universe.csv (and every holding) and writes <run>/triage.csv and
# <run>/gate_batches.json. See process/s3_triage.md for what it decides.
#  (a) return math: EPS growth REQUIRED for the 25% CAGR hurdle per horizon (short 2y, medium 5y, long 7y) at
#      exit P/E = min(own 5y median P/E, 30), with dividends, vs growth VISIBLE in trailing data (conservative, optimistic);
#  (b) earnings evidence (rule 6): E1 acceleration, E2 stalwart rebound, E3 sustained growth, E4 turnaround;
#  (c) flags from the screener figures; only clear failures are rejected here, near-misses go to the gate.
base = run_dir()
HURDLE, MARGIN, BATCH = 0.25, 5, 10
CAPS = (('short', 2, 60), ('medium', 5, 40), ('long', 7, 35))

def num(x):
    try:
        return float(x) if x not in ('', None, 'None', 'nan') else None
    except ValueError:
        return None

U = {r['sym']: r for r in csv.DictReader(open(os.path.join(base, 'universe.csv'), encoding='utf-8'))}
hp = os.path.join(base, 'holdings.csv')
holds = {r['sym'] for r in csv.DictReader(open(hp, encoding='utf-8-sig'))} if os.path.exists(hp) else set()
rows = []
for s in sorted(set(U) | holds):
    u = U.get(s, {})
    g = lambda k: num(u.get(k))
    pe, h5, dy = g('Price to Earning'), g('Historical PE 5Years'), g('Dividend yield') or 0
    qsg, qpg, sg, pg = g('YOY Quarterly sales growth'), g('YOY Quarterly profit growth'), g('Sales growth'), g('Profit growth')
    sg3, pg3, roce = g('Sales growth 3Years'), g('Profit growth 3Years'), g('Return on capital employed')
    prom, pledge, dprom, dprom3 = g('Promoter holding'), g('Pledged percentage'), g('Change in promoter holding'), g('Change in promoter holding 3Years')
    ocf5, ae5 = g('Operating cash flow 5years'), g('Average Earnings 5Year')
    cfoly, cfopy, nply, nppy = g('Cash from operations last year'), g('Cash from operations preceding year'), g('Net Profit last year'), g('Net Profit preceding year')
    r = dict(sym=s, name=u.get('name', ''), hits=u.get('hits', ''), held=s in holds, mcap=g('Market Capitalization'),
             price=g('Current Price'), pe=pe, h5=h5, dy=dy, qsg=qsg, qpg=qpg, sg=sg, pg=pg, sg3=sg3, pg3=pg3, roce=roce,
             de=g('Debt to equity'), prom=prom, pledge=pledge, dprom=dprom, dprom3=dprom3,
             cfo_pat_2y=round((cfoly + cfopy) / (nply + nppy), 2) if None not in (cfoly, cfopy, nply, nppy) and (nply + nppy) > 0 else None,
             cfo_pat_5y=round(ocf5 / (ae5 * 5), 2) if ocf5 is not None and ae5 and ae5 > 0 else None)
    # return math
    r['math'], r['headroom'] = 'no_pe', None
    if pe and pe > 0:
        X = min(h5, 30) if h5 and h5 > 0 else None
        r['X'] = X
        vis = [v for v in (qsg, qpg, sg, pg, sg3, pg3) if v is not None]
        r['g_cons'] = round(max(0, min(qsg or 0, qpg or 0, sg3 if sg3 is not None else 99)), 1)
        r['g_opt'] = round(max(vis), 1) if vis else 0
        if X:
            ok, dead_margin, heads = [], True, []
            for b, years, cap in CAPS:
                m = ((1 + HURDLE) ** years - years * dy / 100) * pe / X
                req = round((m ** (1 / years) - 1) * 100, 1) if m > 0 else -100
                r['g' + b + '_req'] = req
                heads.append(min(r['g_opt'], cap) - req)
                if req <= min(r['g_cons'], cap): ok.append(b + ':strong')
                elif req <= min(r['g_opt'], cap): ok.append(b + ':plausible')
                if req <= min(r['g_opt'], cap) + MARGIN: dead_margin = False
            r['math'] = ' '.join(ok) or ('dead' if dead_margin else 'near')
            r['headroom'] = round(max(heads), 1)
        else:
            r['math'] = 'no_5y_pe'  # recent listing: the gate uses peers
    # earnings evidence
    E = []
    if (qpg or -1) >= 25 and (qsg or -1) >= 20: E.append('E1')
    if (roce or 0) >= 20 and pe and h5 and pe <= 0.8 * h5 and (qsg or -1) >= 0 and (sg3 or -1) >= 8: E.append('E2')
    if min(sg3 if sg3 is not None else -1, pg3 if pg3 is not None else -1) >= 20 and (qsg or -1) >= 15 and (qpg or -1) >= 0: E.append('E3')
    if (qpg or -1) >= 40 and (qsg or -1) >= 15 and (pg3 if pg3 is not None else 0) < 10: E.append('E4')
    r['evidence'] = '+'.join(E)
    # flags (information for the gate) and clear rejects
    flags = []
    if pledge is not None and pledge > 10: flags.append(f'pledge {pledge}%')
    if prom is not None and prom < 50: flags.append(f'promoter {prom}%')
    if dprom is not None and dprom <= -0.5: flags.append(f'promoter {dprom} last qtr')
    if dprom3 is not None and dprom3 < -5: flags.append(f'promoter {dprom3} in 3y')
    c2, c5 = r['cfo_pat_2y'], r['cfo_pat_5y']
    if (c2 is not None and c2 < 0.4) or (c5 is not None and c5 < 0.4): flags.append(f'cash 2y {c2} 5y {c5}')
    if r['de'] is not None and r['de'] > 0.8: flags.append(f"D/E {r['de']}")
    r['flags'] = '; '.join(flags)
    nm = (r['name'] or '').lower()
    if r['held']:
        r['triage'], r['reason'] = 'holding', 'held: goes straight to S9'
    elif 'reit' in nm or 'invit' in nm or ' trust' in nm:
        r['triage'], r['reason'] = 'reject', 'REIT/InvIT'
    elif pledge is not None and pledge > 25:
        r['triage'], r['reason'] = 'reject', f'promoter pledge {pledge}% (rule 1.1)'
    elif c2 is not None and c5 is not None and c2 < 0.3 and c5 < 0.3:
        r['triage'], r['reason'] = 'reject', f'cash conversion 2y {c2}, 5y {c5} (rule 1.4)'
    elif r['math'] == 'dead':
        r['triage'], r['reason'] = 'reject', f"return math fails every horizon by more than {MARGIN} points of growth"
    elif r['math'] == 'no_pe':
        r['triage'], r['reason'] = 'not_queued', 'no positive P/E'
    elif r['hits'] or (r['evidence'] and r['math'] not in ('near',)):
        r['triage'], r['reason'] = 'gate', ('screen ' + r['hits']) if r['hits'] else 'sweep: ' + r['evidence']
    else:
        r['triage'], r['reason'] = 'not_queued', 'not a screen hit; no earnings evidence or math only near the line'
    rows.append(r)

keys = []
for r in rows:
    keys += [k for k in r if k not in keys]
with open(os.path.join(base, 'triage.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)

# gate batches: keep earlier ones, add queued names not yet batched plus <run>/regate.txt
bp = os.path.join(base, 'gate_batches.json')
B = json.load(open(bp, encoding='utf-8')) if os.path.exists(bp) else {'batches': {}}
done = {s for v in B['batches'].values() for s in v}
rg = os.path.join(base, 'regate.txt')
regate = [l.strip() for l in open(rg, encoding='utf-8') if l.strip()] if os.path.exists(rg) else []
new = [r for r in rows if r['triage'] == 'gate' and r['sym'] not in done]
new.sort(key=lambda r: -(r['headroom'] if r['headroom'] is not None else -99))
queue = [r['sym'] for r in new] + [s for s in regate if s not in [r['sym'] for r in new]]
n = max([int(k) for k in B['batches']] + [0])
for i in range(0, len(queue), BATCH):
    n += 1
    B['batches'][str(n)] = queue[i:i + BATCH]
json.dump(B, open(bp, 'w', encoding='utf-8'), indent=1)
if regate:
    open(rg, 'w').write('')
from collections import Counter
print('companies', len(rows), Counter(r['triage'] for r in rows))
print('rejects by reason', Counter(r['reason'].split(' (')[0].split(' ')[0] for r in rows if r['triage'] == 'reject'))
print('new gate batches', len(range(0, len(queue), BATCH)), 'companies', len(queue), '; batches total', n)
