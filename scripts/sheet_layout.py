"""Owns the Google Sheet's layout: every header and formula of the Data, List, Watchlist, Rejected, Allocation and Holdings tabs
(the single List + Watchlist layout, sources/sheet.md), and changes the sheet from the old horizon layout (tabs Short term
101, Medium term 102, Long term 103) to it, or repairs headers, formulas and formats once it is applied. Through the gws CLI.
  python -I scripts/sheet_layout.py [--dry-run] [--out FILE]      the default: read the sheet, save the plan, write nothing
  python -I scripts/sheet_layout.py --apply [--out FILE]          run the plan, read it back, log it
--dry-run reads the tab list, the conditional-format rules and (FORMULA render) Data A1:BG300, List/Watchlist A1:Z200,
  Allocation and Holdings A1:Z100, and builds the ordered plan: 1 renames (101 -> List, 102 -> Watchlist), columns appended to Data when its grid
  ends before the last owned column, and the Rejected tab (108) added when missing (a formula view of Data: status
  Reject, or Exit once no longer held, newest analysis first; hidden Z the ticker list); 2 header texts
  (RAW) and every formula row by row (USER_ENTERED: Data 2-300, List and Watchlist 2-200, Allocation and Holdings 2-100;
  Data, List and Watchlist always in full, Allocation and Holdings only the columns that differ from the owned ones);
  3 clears (Data AW:AX and BE with their headers; List and Watchlist Z3:Z200; Allocation L:M; Holdings K); 4 number
  formats, hidden helper columns W:Z and conditional-format rules (List: the old Sell-trigger rules on J dropped;
  Watchlist: the List rule set); 5 deleting Long term (103), last. Saved as JSON to FILE (default
  runs/sheet_layout_plan.json); prints counts per tab and anything unexpected (an owned formula that differs from the
  sheet's where no change was planned, leftovers in cleared columns, odd rules). Data!BA1 and the Data written columns'
  contents are never touched (only their headers).
--apply runs the same plan (value writes split by wf_lib.sheet_put into calls of at most ~20 KB), then reads back every written
  header and formula (FORMULA render) and every cleared cell and compares them cell by cell; any difference is rewritten
  once, then it fails naming the cells (exit 4). It deletes Long term only after the read-back passes and no formula on the
  five tabs still names a horizon tab. Writes the log runs/sheet_change_<YYYY-MM-DD>.md (what was found before, what was
  written, what was read back).
Refusals (both modes print them, exit 1; --apply writes nothing): Data A2:A300 holds company rows while the old layout
  (tab 103) is still there (they would need migrating); a tab id (101, 102, 7, 104, 106) is missing; the "Formula columns
  (never written)" line of sources/sheet.md does not cover a Data, Allocation or Holdings column the plan fills with
  formulas (List and Watchlist are formula views no script writes; that line does not name them).
Exit codes: 0 done (or plan saved), 1 refused, 2 gws missing or an auth/API error (nothing written after the failing
  call), 4 read-back mismatch after one rewrite. Run from the project root.
"""
import argparse, datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wf_lib as W
from sheet_write import Fail, formula_cols

IDS = {'list': 101, 'watch': 102, 'long': 103, 'alloc': 7, 'hold': 104, 'data': 106, 'rejected': 108}
TITLES = {101: 'List', 102: 'Watchlist', 7: 'Allocation', 104: 'Holdings', 106: 'Data', 108: 'Rejected'}
OLD_TITLES = {101: 'Short term', 102: 'Medium term', 103: 'Long term'}
LAST = {106: 300, 101: 200, 102: 200, 7: 100, 104: 100, 108: 200}
HZ_RE = re.compile(r"'?(Short term|Medium term|Long term)'?!")

# ---------- owned headers and formulas (row-2 form; at_row() moves relative row references) ----------
IMPORTXML = ('IFERROR(VALUE(SUBSTITUTE(INDEX(IMPORTXML(${u}2,"//li[span[contains(normalize-space(.),\'Current Price\')]]'
             '//span[@class=\'number\']"),1),",","")),"")')
FLAG_A = ('=IF($Z2="","",IF($X2=TRUE,HYPERLINK("#gid=10&range=A"&MATCH($Z2,\'Data Flags\'!$A:$A,0),$Z2),$Z2))')
PEND_Z = '=IF($Z2="","",COUNTIF(INDIRECT("\'"&Data!$BA$1&"\'!A:A"),$Z2)>0)'
FLAGC_Z = '=IF($Z2="","",COUNTIF(\'Data Flags\'!$A:$A,$Z2)>0)'


def link(gid, tab, text):
    return f'=IF($Z2="","",IFERROR(HYPERLINK("#gid={gid}&range=A"&MATCH($Z2,{tab}!$Z:$Z,0),"{text}"),""))'


def look(c):
    return f'=IF($Z2="","",INDEX(Data!${c}:${c},MATCH($Z2,Data!$A:$A,0)))'


DATA_HEAD = {
    'A': 'Ticker', 'B': 'Google code (NSE:SYM / BOM:code)', 'C': 'Screener URL', 'D': 'Name', 'E': 'Sector',
    'F': 'Results used', 'G': 'Analysis date', 'H': 'Stored price (screener, last run)', 'I': 'EPS TTM (normalised)',
    'J': 'Base EPS y1', 'K': 'Status', 'L': 'Visible until', 'M': 'Years', 'N': 'Base EPS (at year)', 'O': 'Bear EPS (at year)',
    'P': 'Exit P/E', 'Q': 'Waiting for', 'R': 'Evidence so far', 'S': 'Next check', 'T': 'Exit call',
    'U': 'Top-up: waiting for', 'V': 'Top-up: next check', 'W': 'Dividend / share / year', 'X': 'Evidence quality',
    'AV': '[f] Exit P/E used', 'BB': 'Re-rating evidenced (Y/N)',
    'Y': 'Non-negotiables (Pass / Bent / Fail)', 'Z': 'Bent rules', 'AA': 'Thesis and key reasons',
    'AB': 'Kill condition and review date', 'AC': 'Analysis file', 'AD': '[f] Google price', 'AE': '[f] Screener price',
    'AF': '[f] Price', 'AG': '[f] Price source', 'AH': '[f] P/E now', 'AI': '[f] Fwd P/E', 'AJ': '[f] PEG',
    'AK': '[f] Multiple', 'AL': '[f] CAGR', 'AM': '[f] Bear multiple', 'AN': '[f] Buy below', 'AO': '[f] % above buy below',
    'AP': '[f] Re-rating share', 'AQ': '[f] Below rule (live)', 'AR': '[f] Tab', 'AS': '[f] Watch type',
    'AT': '[f] Waiting for (shown)', 'AU': '[f] Next check (shown)', 'AY': '[f] Results pending', 'AZ': '[f] Data flag',
    'BC': 'Non-negotiables failed (names)', 'BD': '[f] Held', 'BF': 'Stage', 'BG': 'Moat',
    'BH': 'Why rejected / exited', 'BI': 'What would change it'}
DATA_F = {
    # kept as the sheet has them
    'AD': '=IF($A2="","",IFERROR(GOOGLEFINANCE($B2,"price"),""))',
    'AE': '=IF(OR($A2="",ISNUMBER($AD2)),"",' + IMPORTXML.replace('${u}', '$C') + ')',
    'AF': '=IF($A2="","",IF(ISNUMBER($AD2),$AD2,IF(ISNUMBER($AE2),$AE2,$H2)))',
    'AG': '=IF($A2="","",IF(ISNUMBER($AD2),"live",IF(ISNUMBER($AE2),"screener","stored")))',
    'AH': '=IFERROR($AF2/$I2,"")',
    'AI': '=IFERROR($AF2/$J2,"")',
    'AY': '=IF($A2="","",COUNTIF(INDIRECT("\'"&$BA$1&"\'!A:A"),$A2)>0)',
    'AZ': '=IF($A2="","",COUNTIF(\'Data Flags\'!$A:$A,$A2)>0)',
    'BD': '=IF($A2="","",COUNTIF(Holdings!$Z:$Z,$A2)>0)',
    # the projection-year columns
    'AJ': '=IFERROR($AI2/((($N2/$I2)^(1/$M2)-1)*100),"")',
    # the exit P/E used: capped at today's P/E unless Data BB says the re-rating is evidenced
    'AV': '=IF($A2="","",IF(OR($BB2="Y",NOT(ISNUMBER($AH2)),$AH2<=0),$P2,MIN($P2,$AH2)))',
    'AK': '=IF(AND(ISNUMBER($N2),ISNUMBER($AV2),ISNUMBER($M2),ISNUMBER($AF2)),($N2*$AV2+$M2*N($W2))/$AF2,"")',
    'AL': '=IF(ISNUMBER($AK2),$AK2^(1/$M2)-1,"")',
    'AM': '=IF(AND(ISNUMBER($O2),ISNUMBER($AV2),ISNUMBER($M2),ISNUMBER($AF2)),($O2*MIN($AV2,30)+$M2*N($W2))/$AF2,"")',
    'AN': ('=IF(AND(ISNUMBER($N2),ISNUMBER($O2),ISNUMBER($P2),ISNUMBER($M2)),LET(h,1.25^$M2,d,$M2*N($W2),pb,MIN($P2,30),'
           'ev,OR($BB2="Y",NOT(ISNUMBER($I2)),$I2<=0),pc,IF(ev,($N2*$P2+d)/h,IF(($N2*$P2+d)/h>=$P2*$I2,($N2*$P2+d)/h,'
           'IF(d>0,d/(h-$N2/$I2),0))),pbear,IF(ev,($O2*pb+d)/0.8,IF(($O2*pb+d)/0.8>=pb*$I2,($O2*pb+d)/0.8,'
           'IF(d>0,d/(0.8-$O2/$I2),0))),g,IFERROR(($N2/$I2)^(1/$M2)-1,0),ppeg,IFERROR(IF(g>0,2*g*100*$J2,10^99),10^99),'
           'r,MIN(pc,pbear,ppeg),IF(r>0,r,"")),"")'),
    'AO': '=IFERROR($AF2/$AN2-1,"")',
    'AP': '=IFERROR(LN($AV2/$AH2)/LN($AK2),"")',
    'AQ': ('=IF($A2="","",TEXTJOIN(", ",TRUE,IF($Y2="Fail","non-negotiable fail: "&$BC2,""),IF($K2="Exit","exit call: "&$T2,""),'
           'IF(AND(ISNUMBER($AL2),$AL2<0.25),"CAGR below 25%",""),IF(AND(ISNUMBER($AM2),$AM2<0.8),"bear below 0.8x",""),'
           'IF(AND(ISNUMBER($AJ2),OR($AJ2>2,$AJ2<0)),"PEG above 2 or negative",""),'
           'IF(AND(ISNUMBER($AI2),$AI2<0),"forward P/E negative","")))'),
    'AR': ('=IF($A2="","",IF($BD2=TRUE,"List",IF($K2="List",IF(AND(ISNUMBER($AL2),$AL2>=0.25,ISNUMBER($AM2),$AM2>=0.8,'
           'NOT(AND(ISNUMBER($AJ2),OR($AJ2>2,$AJ2<0))),NOT(AND(ISNUMBER($AI2),$AI2<0))),"List","Watch"),'
           'IF($K2="Watch","Watch",""))))'),
    'AS': ('=IF($A2="","",IF(AND($BD2=TRUE,$U2<>""),"Top-up",IF($AR2="Watch",IF($K2="Watch","Entry: evidence",'
           '"Entry: price"),"")))'),
    'AT': ('=IF($AS2="","",IF($AS2="Top-up",$U2,IF($AS2="Entry: evidence",$Q2,IF(ISNUMBER($AN2),"price at or below "&'
           'TEXT($AN2,"#,##0.00"),"re-rating evidence or faster growth (no price clears the hurdle)"))))'),
    'AU': '=IF($AS2="","",IF($AS2="Top-up",$V2,IF($AS2="Entry: evidence",$S2,"")))',
}
DATA_CLEAR = ['AW', 'AX', 'BE']   # header and contents

TAIL_HEAD = {'W': '[h] price source', 'X': '[h] flag', 'Y': '[h] pending', 'Z': '[h] list'}
TAIL_F = {'W': look('AG'), 'X': look('AZ'), 'Y': look('AY')}
LIST_COLS = [('A', 'Ticker', FLAG_A), ('B', 'Name', look('D')), ('C', 'Sector', look('E')), ('D', 'Price', look('AF')),
             ('E', 'Expected CAGR', look('AL')), ('F', 'Base multiple', look('AK')), ('G', 'Bear multiple', look('AM')),
             ('H', 'Visible until', look('L')), ('I', 'Years', look('M')),
             ('J', 'Status', '=IF($Z2="","",IF(INDEX(Data!$BD:$BD,MATCH($Z2,Data!$A:$A,0))=TRUE,IF(INDEX(Data!$K:$K,'
                             'MATCH($Z2,Data!$A:$A,0))="Exit","Held: exit call","Held"),"Candidate"))'),
             ('K', 'Exit P/E (used)', look('AV')), ('L', 'P/E now', look('AH')), ('M', 'Fwd P/E', look('AI')), ('N', 'PEG', look('AJ')),
             ('O', 'Re-rating share', look('AP')), ('P', 'Evidence / moat', '=IF($Z2="","",INDEX(Data!$X:$X,MATCH($Z2,Data!$A:$A,0))&IF(INDEX(Data!$BG:$BG,MATCH($Z2,Data!$A:$A,0))="",""," / moat: "&INDEX(Data!$BG:$BG,MATCH($Z2,Data!$A:$A,0))))'), ('Q', 'Non-negotiables', look('Y')),
             ('R', 'Results used', look('F')), ('S', 'Thesis', look('AA')), ('T', 'Stage', look('BF')),
             ('U', 'Exit call', look('T')), ('V', 'Below rule (live)', look('AQ'))]
WATCH_COLS = [('A', 'Ticker', FLAG_A), ('B', 'Name', look('D')), ('C', 'Sector', look('E')), ('D', 'Price', look('AF')),
              ('E', 'Expected CAGR', look('AL')), ('F', 'Type', look('AS')), ('G', 'Waiting for', look('AT')),
              ('H', 'Evidence so far', look('R')), ('I', 'Next check', look('AU')), ('J', 'Buy below', look('AN')),
              ('K', '% above buy below', look('AO')), ('L', 'Visible until', look('L')), ('M', 'Years', look('M')),
              ('N', 'Exit P/E (used)', look('AV')), ('O', 'P/E now', look('AH')), ('P', 'Evidence / moat', '=IF($Z2="","",INDEX(Data!$X:$X,MATCH($Z2,Data!$A:$A,0))&IF(INDEX(Data!$BG:$BG,MATCH($Z2,Data!$A:$A,0))="",""," / moat: "&INDEX(Data!$BG:$BG,MATCH($Z2,Data!$A:$A,0))))'),
              ('Q', 'Non-negotiables', look('Y')), ('R', 'Results used', look('F')), ('S', 'Thesis', look('AA')),
              ('T', 'Stage', look('BF')),
              ('U', 'Held', '=IF($Z2="","",IF(INDEX(Data!$BD:$BD,MATCH($Z2,Data!$A:$A,0))=TRUE,"Yes",""))'),
              ('V', 'Below rule (live)', look('AQ'))]
def zlook(c):
    return f'=IF($Z2="","",INDEX(Data!${c}:${c},MATCH($Z2,Data!$A:$A,0)))'


REJ_FILT = '(Data!$K$2:$K$300="Reject")+((Data!$K$2:$K$300="Exit")*(Data!$BD$2:$BD$300<>TRUE))'
REJ_COLS = [('A', 'Ticker', '=IF($Z2="","",$Z2)'), ('B', 'Name', zlook('D')), ('C', 'Sector', zlook('E')),
            ('D', 'Status', '=IF($Z2="","",IF(INDEX(Data!$K:$K,MATCH($Z2,Data!$A:$A,0))="Exit","Exited","Rejected"))'),
            ('E', 'Analysis date', zlook('G')), ('F', 'Results used', zlook('F')), ('G', 'Why', zlook('BH')),
            ('H', 'What would change it', zlook('BI')), ('I', 'Price at analysis', zlook('H')), ('J', 'Price now', zlook('AF')),
            ('K', 'Analysis file', zlook('AC'))]
REJ_Z2 = ('=IFERROR(INDEX(SORT(FILTER({Data!$A$2:$A$300,Data!$G$2:$G$300},' + REJ_FILT + '),2,FALSE),0,1),"")')
REJ_NF = dict(E='text', F='text', G='text', H='text', I='price', J='price', K='text')
LIST_Z2 = ('=IFERROR(INDEX(SORT(FILTER({Data!$A$2:$A$300,ARRAYFORMULA(IF(ISNUMBER(Data!$AL$2:$AL$300),Data!$AL$2:$AL$300,-1))},Data!$AR$2:$AR$300="List"),2,FALSE),0,1),"")')
WATCH_Z2 = ('=IFERROR(INDEX(SORT(FILTER({Data!$A$2:$A$300,Data!$AS$2:$AS$300,ARRAYFORMULA(IF(ISNUMBER(Data!$AL$2:$AL$300),Data!$AL$2:$AL$300,-1))},Data!$AS$2:$AS$300<>""),2,TRUE,3,FALSE),0,1),"")')
# SORT is given one array with its keys as extra columns: a FILTER result as SORT's sort column gives #VALUE!

ALLOC_HEAD = {'A': 'Ticker', 'B': 'Name', 'C': 'Action', 'D': 'Target weight', 'E': 'Target value (₹)',
              'F': 'Current value (₹)', 'G': 'Price', 'H': 'Buy below (₹)', 'I': 'Trim above (weight)', 'J': 'List',
              'K': 'Watchlist', 'N': 'Notes', 'W': '[h] price source', 'X': '[h] flag', 'Y': '[h] pending',
              'Z': 'Ticker (source)'}
ALLOC_F = {
    'A': FLAG_A,
    'F': '=IF($Z2="","",IFERROR(INDEX(Holdings!$G:$G,MATCH($Z2,Holdings!$Z:$Z,0)),0))',
    'G': ('=IF($Z2="","",IFERROR(INDEX(Data!$AF:$AF,MATCH($Z2,Data!$A:$A,0)),IFERROR(INDEX(Holdings!$E:$E,'
          'MATCH($Z2,Holdings!$Z:$Z,0)),"")))'),
    'J': link(101, 'List', 'List'), 'K': link(102, 'Watchlist', 'Watchlist'),
    'W': ('=IF($Z2="","",IFERROR(INDEX(Data!$AG:$AG,MATCH($Z2,Data!$A:$A,0)),IFERROR(INDEX(Holdings!$W:$W,'
          'MATCH($Z2,Holdings!$Z:$Z,0)),"")))'),
    'X': FLAGC_Z, 'Y': PEND_Z}
ALLOC_BLOCK = [['Check', 'Rule', 'Target', 'Current'],
               ['Largest position', 'target ~7%, trim above 15%', '=IFERROR(MAX($D$2:$D$100),"")',
                '=IFERROR(MAX($F$2:$F$100)/SUM(Holdings!$G$2:$G$100),"")'],
               ['Total target weight', 'unfilled weight in a liquid fund', '=SUM($D$2:$D$100)', ''],
               ['Positions', 'as many as pass; at most 2 per sector', '=COUNT($D$2:$D$100)',
                '=COUNTIF(Holdings!$C$2:$C$100,">0")']]
ALLOC_CLEAR = ['L', 'M']
HOLD_HEAD = {'A': 'Ticker', 'B': 'Name', 'C': 'Qty', 'D': 'Avg cost', 'E': 'Price', 'F': 'Status', 'G': 'Value', 'H': 'P&L',
             'I': 'List', 'J': 'Watchlist', 'L': 'P&L %', 'N': 'Google code', 'O': 'Screener URL', 'P': 'Stored price',
             'Q': 'Kite stale', 'R': '[h] Google price', 'S': '[h] Screener price', 'V': '[h] ISIN', 'W': '[h] price source',
             'X': '[h] flag', 'Y': '[h] pending', 'Z': 'Ticker (source)'}   # M1 carries kite_holdings.py's fetch stamp
HOLD_F = {
    'A': FLAG_A, 'E': '=IF($Z2="","",IF(ISNUMBER($R2),$R2,IF(ISNUMBER($S2),$S2,$P2)))',
    'G': '=IF(OR($Z2="",$C2=""),"",$C2*$E2)', 'H': '=IF(OR($Z2="",$C2=""),"",($E2-$D2)*$C2)',
    'I': link(101, 'List', 'List'), 'J': link(102, 'Watchlist', 'Watchlist'), 'L': '=IFERROR($E2/$D2-1,"")',
    'R': '=IF($Z2="","",IFERROR(GOOGLEFINANCE($N2,"price"),""))',
    'S': '=IF(OR($Z2="",ISNUMBER($R2)),"",' + IMPORTXML.replace('${u}', '$O') + ')',
    'W': '=IF($Z2="","",IF(ISNUMBER($R2),"live",IF(ISNUMBER($S2),"screener","stored")))', 'X': FLAGC_Z, 'Y': PEND_Z}
HOLD_CLEAR = ['K']
EXPECTED_CHANGE = {7: {'I1', 'J', 'K', 'L', 'M'}, 104: {'I', 'J', 'K'}}

# ---------- formats and conditional formats ----------
NF = {'price': {'type': 'NUMBER', 'pattern': '#,##0.00'}, 'pct1': {'type': 'PERCENT', 'pattern': '0.0%'},
      'pct0': {'type': 'PERCENT', 'pattern': '0%'}, 'mult': {'type': 'NUMBER', 'pattern': '0.00"x"'},
      'pe': {'type': 'NUMBER', 'pattern': '0.0'}, 'int': {'type': 'NUMBER', 'pattern': '0'}, 'text': {'type': 'TEXT'}}
LIST_NF = dict(D='price', E='pct1', F='mult', G='mult', H='text', I='int', J='text', K='pe', L='pe', M='pe', N='pe',
               O='pct0', **{c: 'text' for c in 'PQRSTUV'})
WATCH_NF = dict(D='price', E='pct1', F='text', G='text', H='text', I='text', J='price', K='pct1', L='text', M='int',
                N='pe', O='pe', **{c: 'text' for c in 'PQRSTUV'})
RED = {'red': 0.7490196, 'green': 0.09803922, 'blue': 0.09803922}
BG = {'flag': {'red': 0.95686275, 'green': 0.8, 'blue': 0.8}, 'pend': {'red': 1, 'green': 0.9490196, 'blue': 0.7490196},
      'scr': {'red': 0.9882353, 'green': 0.8784314, 'blue': 0.7490196},
      'stored': {'red': 0.8784314, 'green': 0.8784314, 'blue': 0.8784314}}
# (formula, first column, last column + 1, fill or None, red text): the List rule set, in priority order
CF_RULES = [('=AND($X2=TRUE,$V2<>"")', 0, 1, 'flag', True), ('=$X2=TRUE', 0, 1, 'flag', False),
            ('=AND($Y2=TRUE,$V2<>"")', 0, 1, 'pend', True), ('=$Y2=TRUE', 0, 1, 'pend', False),
            ('=AND($W2="screener",$V2<>"")', 3, 4, 'scr', True), ('=$W2="screener"', 3, 4, 'scr', False),
            ('=AND($W2="stored",$V2<>"")', 3, 4, 'stored', True), ('=$W2="stored"', 3, 4, 'stored', False),
            ('=AND($Y2=TRUE,$V2<>"")', 3, 4, 'pend', True), ('=$Y2=TRUE', 3, 4, 'pend', False),
            ('=AND($Y2=TRUE,$V2<>"")', 0, 22, 'pend', True), ('=$Y2=TRUE', 0, 22, 'pend', False),
            ('=$V2<>""', 0, 22, None, True)]
CF_NAMES = ['A flag + red', 'A flag', 'A pending + red', 'A pending', 'D screener + red', 'D screener', 'D stored + red',
            'D stored', 'D pending + red', 'D pending', 'A:V pending + red', 'A:V pending', 'A:V red text']


def at_row(f, r):
    """A row-2 formula moved to row r: relative row references ($X2, X2) outside string literals; $X$2 stays."""
    parts = re.split(r'("(?:[^"]|"")*")', f)
    rx = re.compile(r'(?<![A-Za-z0-9$_])(\$?[A-Z]{1,3})2(?![0-9])')
    return ''.join(p if i % 2 else rx.sub(lambda m: f'{m.group(1)}{r}', p) for i, p in enumerate(parts))


def rnd(c):
    return tuple(round(float((c or {}).get(k, 0)), 4) for k in ('red', 'green', 'blue')) if c else None


def cf_norm(rule):
    b = rule.get('booleanRule') or {}
    vals = [v.get('userEnteredValue') for v in (b.get('condition') or {}).get('values') or []]
    f = b.get('format') or {}
    return (tuple(vals), tuple((g.get('startRowIndex'), g.get('endRowIndex'), g.get('startColumnIndex'), g.get('endColumnIndex'))
                               for g in rule.get('ranges') or []),
            rnd(f.get('backgroundColor')), rnd((f.get('textFormat') or {}).get('foregroundColor')))


def cf_rule(sid, x):
    formula, c0, c1, bg, red = x
    fmt = {}
    if bg:
        fmt['backgroundColor'] = BG[bg]
    if red:
        fmt['textFormat'] = {'foregroundColor': RED}
    return {'ranges': [{'sheetId': sid, 'startRowIndex': 1, 'endRowIndex': 200, 'startColumnIndex': c0, 'endColumnIndex': c1}],
            'booleanRule': {'condition': {'type': 'CUSTOM_FORMULA', 'values': [{'userEnteredValue': formula}]}, 'format': fmt}}


# ---------- the desired cells ----------
def desired():
    """{sheetId: {'head': {col: text}, 'f': {col: {row: formula}}, 'clear': [ranges], 'mode': 'all'|'diff'}}."""
    def rows(fs, last):
        return {c: {r: at_row(f, r) for r in range(2, last + 1)} for c, f in fs.items()}
    out = {106: {'head': dict(DATA_HEAD), 'f': rows(DATA_F, 300), 'mode': 'all',
                 'clear': [f'{c}1:{c}300' for c in DATA_CLEAR]}}
    for sid, cols, z2 in ((101, LIST_COLS, LIST_Z2), (102, WATCH_COLS, WATCH_Z2)):
        head = {c: h for c, h, _ in cols}
        head.update(TAIL_HEAD)
        fs = rows({c: f for c, _, f in cols}, 200)
        fs.update(rows(TAIL_F, 200))
        fs['Z'] = {2: z2}
        out[sid] = {'head': head, 'f': fs, 'mode': 'all', 'clear': ['Z3:Z200']}
    fs = rows({c: f for c, _, f in REJ_COLS}, 200)
    fs['Z'] = {2: REJ_Z2}
    out[108] = {'head': dict({c: h for c, h, _ in REJ_COLS}, Z='[h] ticker'), 'f': fs, 'mode': 'all', 'clear': ['Z3:Z200']}
    af = rows(ALLOC_F, 100)
    for i, row in enumerate(ALLOC_BLOCK[1:], 2):
        for j, v in enumerate(row[2:], 2):
            if v:
                af.setdefault('PQRS'[j], {})[i] = v
    ah = dict(ALLOC_HEAD)
    ah.update(dict(zip('PQRS', ALLOC_BLOCK[0])))
    out[7] = {'head': ah, 'f': af, 'mode': 'diff', 'clear': [f'{c}1:{c}100' for c in ALLOC_CLEAR] + ['S3'],
              'text': {(c, r): ALLOC_BLOCK[r - 1][j] for r in (2, 3, 4) for j, c in enumerate('PQ')}}
    out[104] = {'head': dict(HOLD_HEAD), 'f': rows(HOLD_F, 100), 'mode': 'diff', 'clear': [f'{c}1:{c}100' for c in HOLD_CLEAR]}
    return out


def cell(vals, col, r):
    """A cell of a 2-D answer read from A1."""
    row = vals[r - 1] if r - 1 < len(vals) else []
    i = W.col_index(col)
    return row[i] if i < len(row) else ''


# ---------- reading and planning ----------
def read_sheet():
    k = W.gws_mod()
    meta = k.gws('sheets', 'spreadsheets', 'get', '--params', json.dumps(
        {'spreadsheetId': k.SHEET, 'fields': 'sheets(properties(sheetId,title,gridProperties),conditionalFormats)'}))
    tabs = {s['properties']['sheetId']: s for s in meta.get('sheets', [])}
    titles = {sid: s['properties']['title'] for sid, s in tabs.items()}
    want = [(sid, 'Z' if sid in (101, 102, 7, 104, 108) else 'BI') for sid in (106, 101, 102, 7, 104, 103, 108) if sid in titles]
    vals = W.sheet_get([f'{W.quote_tab(titles[sid])}!A1:{c}{LAST.get(sid, 200)}' for sid, c in want], 'FORMULA')
    return tabs, titles, {sid: v for (sid, _), v in zip(want, vals)}


def build_plan(tabs, titles, vals):
    refusals, unexpected, counts = [], [], {}
    missing = [sid for sid in (101, 102, 7, 104, 106) if sid not in titles]
    if missing:
        refusals.append(f'tab ids missing: {missing}')
    old = 103 in titles
    data = vals.get(106, [])
    company = [str(cell(data, 'A', r)) for r in range(2, 301) if str(cell(data, 'A', r)).strip()]
    if old and company:
        refusals.append(f'Data A2:A300 holds {len(company)} company rows ({", ".join(company[:5])}...) while the old layout '
                        'is still there: they would need migrating to the new columns first')
    want = desired()
    try:
        fc = formula_cols()
        for sid, tab in ((106, 'Data'), (7, 'Allocation'), (104, 'Holdings')):
            filled = set(want[sid]['f'])
            bad = sorted(filled - fc.get(tab, set()), key=W.col_index)
            if bad:
                refusals.append(f'sources/sheet.md formula-columns line does not cover {tab} {bad}, which the plan fills with formulas')
    except Fail as e:
        refusals.append(str(e))
    ba1 = cell(data, 'BA', 1)
    if not re.match(r'^Pending .* results$', str(ba1)):
        unexpected.append(f'Data!BA1 holds {ba1!r}, not a pending tab name (left as it is)')
    for sid in (101, 102):
        t = titles.get(sid)
        if t and t not in (TITLES[sid], OLD_TITLES[sid]):
            unexpected.append(f'tab {sid} is named {t!r} (expected {OLD_TITLES[sid]!r} or {TITLES[sid]!r})')
    clash = [t for sid, t in titles.items() if t in ('List', 'Watchlist') and sid not in (101, 102)]
    if clash:
        refusals.append(f'another tab already has the name {clash}')

    steps = []
    ren = [{'updateSheetProperties': {'properties': {'sheetId': sid, 'title': TITLES[sid]}, 'fields': 'title'}}
           for sid in (101, 102) if sid in titles and titles[sid] != TITLES[sid]]
    if ren:
        steps.append({'step': 'renames', 'method': 'spreadsheets.batchUpdate', 'requests': ren})
    need = max(W.col_index(c) for c in DATA_HEAD) + 1
    have = ((tabs.get(106) or {}).get('properties', {}).get('gridProperties') or {}).get('columnCount', need)
    if have < need:
        steps.append({'step': 'widen Data', 'method': 'spreadsheets.batchUpdate', 'requests': [
            {'appendDimension': {'sheetId': 106, 'dimension': 'COLUMNS', 'length': need - have}}]})
    if 108 not in titles:
        steps.append({'step': 'add Rejected', 'method': 'spreadsheets.batchUpdate', 'requests': [
            {'addSheet': {'properties': {'sheetId': 108, 'title': TITLES[108],
                                         'gridProperties': {'rowCount': 200, 'columnCount': 26}}}}]})
    raw, user, clears = [], [], []
    for sid in (106, 101, 102, 7, 104, 108):
        if sid not in titles and sid != 108:
            continue
        w, v, q = want[sid], vals.get(sid, []), W.quote_tab(TITLES[sid])
        n = {'headers': 0, 'formula cells': 0, 'cleared ranges': 0}
        diff_cols = set()
        for c, h in w['head'].items():
            if w['mode'] == 'all' or str(cell(v, c, 1)) != h:
                raw.append({'range': f'{q}!{c}1', 'values': [[h]]})
                n['headers'] += 1
                if str(cell(v, c, 1)) != h:
                    diff_cols.add(f'{c}1' if sid == 7 and c == 'I' else c)
        for (c, r), t in (w.get('text') or {}).items():
            if str(cell(v, c, r)) != t:
                raw.append({'range': f'{q}!{c}{r}', 'values': [[t]]})
                n['headers'] += 1
        for c, fr in w['f'].items():
            rs = sorted(fr)
            differs = [r for r in rs if str(cell(v, c, r)) != fr[r]]
            if sid == 106 and c in ('AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AY', 'AZ', 'BD') and differs:
                unexpected.append(f'Data {c}: {len(differs)} rows differ from the formula kept from today (first: row {differs[0]}); rewritten')
            if w['mode'] == 'all' or differs:
                if w['mode'] == 'diff' and differs:
                    diff_cols.add(c)
                # contiguous runs of rows
                runs, cur = [], [rs[0]]
                for r in rs[1:]:
                    if r == cur[-1] + 1:
                        cur.append(r)
                    else:
                        runs.append(cur)
                        cur = [r]
                runs.append(cur)
                for run in runs:
                    user.append({'range': f'{q}!{c}{run[0]}:{c}{run[-1]}', 'values': [[fr[r]] for r in run]})
                    n['formula cells'] += len(run)
        for rg in w['clear']:
            clears.append(f'{q}!{rg}')
            n['cleared ranges'] += 1
            m = re.match(r'([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$', rg)
            c0, r0, c1, r1 = m.group(1), int(m.group(2)), m.group(3) or m.group(1), int(m.group(4) or m.group(2))
            left = [f'{W.col_letters(ci)}{r}' for ci in range(W.col_index(c0), W.col_index(c1) + 1)
                    for r in range(max(r0, 2), r1 + 1) if str(cell(v, W.col_letters(ci), r)) != '']
            # old formulas in the retired columns are expected while the old layout is there; data or spill cells never
            data_like = (sid == 106 and c0 == 'BE') or (sid in (101, 102) and c0 == 'Z')
            if left and (data_like or not old):
                unexpected.append(f'{TITLES[sid]} {rg}: {len(left)} non-empty cells cleared (first {left[0]})')
        if sid in EXPECTED_CHANGE:
            odd = sorted(diff_cols - EXPECTED_CHANGE[sid] - {'P', 'Q', 'R', 'S'})
            if odd:
                unexpected.append(f'{TITLES[sid]}: columns {odd} differ from the owned headers/formulas outside the planned change; rewritten')
        counts[TITLES[sid]] = n
    if raw:
        steps.append({'step': 'header texts', 'method': 'values.batchUpdate', 'valueInputOption': 'RAW', 'data': raw})
    if user:
        steps.append({'step': 'formulas', 'method': 'values.batchUpdate', 'valueInputOption': 'USER_ENTERED', 'data': user})
    if clears:
        steps.append({'step': 'clears', 'method': 'values.batchClear', 'ranges': clears})

    fmt, cf_report = [], {}
    for sid, nf in ((101, LIST_NF), (102, WATCH_NF)):
        for c, k in nf.items():
            ci = W.col_index(c)
            fmt.append({'repeatCell': {'range': {'sheetId': sid, 'startRowIndex': 1, 'endRowIndex': 200, 'startColumnIndex': ci,
                                                 'endColumnIndex': ci + 1},
                                       'cell': {'userEnteredFormat': {'numberFormat': NF[k]}}, 'fields': 'userEnteredFormat.numberFormat'}})
        fmt.append({'updateDimensionProperties': {'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 22, 'endIndex': 26},
                                                  'properties': {'hiddenByUser': True}, 'fields': 'hiddenByUser'}})
    for c, k in REJ_NF.items():
        ci = W.col_index(c)
        fmt.append({'repeatCell': {'range': {'sheetId': 108, 'startRowIndex': 1, 'endRowIndex': 200, 'startColumnIndex': ci,
                                             'endColumnIndex': ci + 1},
                                   'cell': {'userEnteredFormat': {'numberFormat': NF[k], 'wrapStrategy': 'WRAP'}},
                                   'fields': 'userEnteredFormat.numberFormat,userEnteredFormat.wrapStrategy'}})
    fmt.append({'updateDimensionProperties': {'range': {'sheetId': 108, 'dimension': 'COLUMNS', 'startIndex': 25, 'endIndex': 26},
                                              'properties': {'hiddenByUser': True}, 'fields': 'hiddenByUser'}})
    for (r0, r1, c0, c1), k in (((1, 100, 8, 9), 'pct1'), ((1, 3, 17, 18), 'pct1'), ((1, 2, 18, 19), 'pct1'), ((3, 4, 17, 19), 'int')):
        fmt.append({'repeatCell': {'range': {'sheetId': 7, 'startRowIndex': r0, 'endRowIndex': r1, 'startColumnIndex': c0,
                                             'endColumnIndex': c1},
                                   'cell': {'userEnteredFormat': {'numberFormat': NF[k]}}, 'fields': 'userEnteredFormat.numberFormat'}})
    goal = [cf_norm(cf_rule(0, x)) for x in CF_RULES]
    for sid in (101, 102):
        if sid not in tabs:
            continue
        cur = tabs[sid].get('conditionalFormats') or []
        norm = [cf_norm(r) for r in cur]
        mine = goal   # cf_norm leaves the sheetId out, so the goal compares on any tab
        if norm == mine:
            cf_report[TITLES[sid]] = {'kept': len(cur), 'dropped': [], 'added': []}
            continue
        jidx = [i for i, x in enumerate(norm) if all(g[2] == 9 and g[3] == 10 for g in x[1])]
        if sid == 101 and [x for i, x in enumerate(norm) if i not in jidx] == mine:
            fmt += [{'deleteConditionalFormatRule': {'sheetId': sid, 'index': i}} for i in sorted(jidx, reverse=True)]
            cf_report[TITLES[sid]] = {'kept': len(cur) - len(jidx),
                                      'dropped': [f'#{i} {norm[i][0][0]} on J' for i in jidx], 'added': []}
        else:
            fmt += [{'deleteConditionalFormatRule': {'sheetId': sid, 'index': i}} for i in range(len(cur) - 1, -1, -1)]
            fmt += [{'addConditionalFormatRule': {'rule': cf_rule(sid, x), 'index': i}} for i, x in enumerate(CF_RULES)]
            cf_report[TITLES[sid]] = {'kept': 0, 'dropped': [f'#{i} {x[0][0]} cols {x[1]}' for i, x in enumerate(norm)],
                                      'added': CF_NAMES}
            if sid == 101:
                unexpected.append('List conditional formats did not match the known Short-term set: all replaced')
    for sid in (7, 104, 106):
        if sid in tabs:
            cf_report[TITLES[sid]] = {'kept': len(tabs[sid].get('conditionalFormats') or []), 'dropped': [], 'added': []}
    steps.append({'step': 'formats and conditional formats', 'method': 'spreadsheets.batchUpdate', 'requests': fmt})
    if old:
        steps.append({'step': 'delete Long term', 'method': 'spreadsheets.batchUpdate', 'requests': [{'deleteSheet': {'sheetId': 103}}]})
    return {'spreadsheetId': W.gws_mod().SHEET, 'state': 'old layout' if old else 'applied layout (repair only)',
            'tabs_found': {str(k): v for k, v in titles.items()}, 'company_rows_in_data': len(company),
            'refusals': refusals, 'unexpected': unexpected, 'counts': counts, 'conditional_formats': cf_report,
            'steps': steps,
            'read_back': 'every header/formula range in the value steps read with valueRenderOption FORMULA and compared '
                         'cell by cell; every cleared range must read back empty'}


# ---------- applying ----------
def gws_call(method, body):
    k = W.gws_mod()
    parts = method.split('.')
    return k.gws('sheets', 'spreadsheets', *parts, '--params', json.dumps({'spreadsheetId': k.SHEET}), body=body)


def put(data, option):
    W.sheet_put([(d['range'], d['values']) for d in data], option)   # split into calls of at most ~20 KB


def clear(ranges):
    for i in range(0, len(ranges), 50):
        gws_call('values.batchClear', {'ranges': ranges[i:i + 50]})


def expand(rg):
    """'Tab!C3:D4' -> (tab, [(col, row), ...])."""
    tab, a = rg.rsplit('!', 1)
    m = re.match(r'([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$', a)
    c0, r0, c1, r1 = m.group(1), int(m.group(2)), m.group(3) or m.group(1), int(m.group(4) or m.group(2))
    return tab, [(W.col_letters(ci), r) for r in range(r0, r1 + 1) for ci in range(W.col_index(c0), W.col_index(c1) + 1)]


def check(plan):
    """Cells that differ from the plan: [(step data item or clear range, cell, expected, got)]."""
    items = [(d, d['values']) for s in plan['steps'] if s['method'] == 'values.batchUpdate' for d in s['data']]
    items += [({'range': r, 'clear': True}, None) for s in plan['steps'] if s['method'] == 'values.batchClear' for r in s['ranges']]
    bad = []
    for i in range(0, len(items), 40):
        part = items[i:i + 40]
        got = W.sheet_get([d['range'] for d, _ in part], 'FORMULA')
        for (d, v), g in zip(part, got):
            _, cells = expand(d['range'])
            r0, c0 = cells[0][1], W.col_index(cells[0][0])
            for c, r in cells:
                gi, gj = r - r0, W.col_index(c) - c0
                gv = g[gi][gj] if gi < len(g) and gj < len(g[gi]) else ''
                ev = '' if v is None else v[gi][gj]
                if str(gv) != str(ev):
                    bad.append((d, f'{d["range"].rsplit("!", 1)[0]}!{c}{r}', ev, gv))
    return bad


def horizon_refs():
    """Formulas on the five tabs that still name a horizon tab."""
    left = []
    for t, rg in (('Data', 'A1:BG300'), ('List', 'A1:Z200'), ('Watchlist', 'A1:Z200'), ('Allocation', 'A1:Z100'),
                  ('Holdings', 'A1:Z100')):
        v, = W.sheet_get([f'{t}!{rg}'], 'FORMULA')
        for i, row in enumerate(v):
            for j, x in enumerate(row):
                if isinstance(x, str) and HZ_RE.search(x):
                    left.append(f'{t}!{W.col_letters(j)}{i + 1}')
    return left


def apply(plan):
    log = []
    for s in plan['steps']:
        if s['step'] == 'delete Long term':
            continue
        if s['method'] == 'spreadsheets.batchUpdate' and s['requests']:
            gws_call('batchUpdate', {'requests': s['requests']})
        elif s['method'] == 'values.batchUpdate':
            put(s['data'], s['valueInputOption'])
        elif s['method'] == 'values.batchClear':
            clear(s['ranges'])
        log.append(f"- {s['step']}: done ({len(s.get('data') or s.get('ranges') or s.get('requests') or [])} items)")
    bad = check(plan)
    log.append(f'- read-back 1: {len(bad)} cells differ')
    if bad:
        redo = {id(d): d for d, *_ in bad}
        raw = [d for d in redo.values() if 'values' in d and not str(d['values'][0][0]).startswith('=')]
        usr = [d for d in redo.values() if 'values' in d and str(d['values'][0][0]).startswith('=')]
        if raw:
            put(raw, 'RAW')
        if usr:
            put(usr, 'USER_ENTERED')
        cl = [d['range'] for d in redo.values() if d.get('clear')]
        if cl:
            clear(cl)
        bad = check(plan)
        log.append(f'- read-back 2 after one rewrite: {len(bad)} cells differ')
        if bad:
            return log, 'READ-BACK MISMATCH after one rewrite: ' + '; '.join(f'{c} wrote {e!r} got {g!r}' for _, c, e, g in bad[:10])
    dele = [s for s in plan['steps'] if s['step'] == 'delete Long term']
    if dele:
        left = horizon_refs()
        if left:
            return log, f'Long term NOT deleted: formulas still name a horizon tab: {left[:10]}'
        gws_call('batchUpdate', {'requests': dele[0]['requests']})
        log.append('- Long term (103) deleted')
        bad = check(plan)
        log.append(f'- read-back after the deletion: {len(bad)} cells differ')
        if bad:
            return log, 'READ-BACK MISMATCH after the deletion: ' + '; '.join(f'{c} got {g!r}' for _, c, e, g in bad[:10])
    return log, None


def summary(plan):
    out = [f"state: {plan['state']}; tabs {plan['tabs_found']}; Data company rows {plan['company_rows_in_data']}"]
    for t, n in plan['counts'].items():
        out.append(f"{t}: {n['headers']} header/text cells, {n['formula cells']} formula cells, {n['cleared ranges']} cleared ranges")
    for t, c in plan['conditional_formats'].items():
        out.append(f"{t} conditional formats: kept {c['kept']}, dropped {len(c['dropped'])}, added {len(c['added'])}")
    out.append('steps: ' + ', '.join(s['step'] for s in plan['steps']))
    out += [f'UNEXPECTED: {u}' for u in plan['unexpected']]
    out += [f'REFUSED: {r}' for r in plan['refusals']]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', help='read the sheet, save the plan, write nothing (the default)')
    g.add_argument('--apply', action='store_true', help='run the plan through gws, read it back, write the log')
    ap.add_argument('--out', default=os.path.join('runs', 'sheet_layout_plan.json'), help='where the plan JSON goes')
    a = ap.parse_args()
    try:
        tabs, titles, vals = read_sheet()
        plan = build_plan(tabs, titles, vals)
        W.write_json(a.out, plan)
        lines = summary(plan)
        for x in lines:
            print(x)
        print(f'plan saved: {a.out}')
        if plan['refusals']:
            return 1
        if not a.apply:
            return 0
        log, err = apply(plan)
        day = dt.date.today().isoformat()
        lp = os.path.join('runs', f'sheet_change_{day}.md')
        W.write_text(lp, '\n'.join([f'# Sheet layout change {day}', '', '## Found before', ''] + [f'- {x}' for x in lines] +
                                   ['', '## Written', '', f'Plan: {a.out}', ''] + log +
                                   ['', '## Read back', '', err or 'every written header and formula and every cleared cell matched']) + '\n')
        print(f'log: {lp}')
        if err:
            print(err, file=sys.stderr)
            return 4
        print('applied and read back')
        return 0
    except Fail as e:
        print(str(e), file=sys.stderr)
        return e.code
    except W.gws_mod().SheetError as e:
        print(f'SHEET ERROR (nothing written after this call): {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
