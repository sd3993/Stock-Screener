# S8.0: gate, one batch (deep tier; full mode)

Decide NEXT or REJECT for each company in your batch, from its figures, its latest guidance and its last 12 months of exchange filings, to the gate standard in `/principles/filter_rules.md`. Do not edit any existing file except a company's `index.json` when you download a filing. Working directory: the project root (PowerShell). Your brief gives the run folder, the batch number and whether the data was pre-fetched by script.

## Read first
`/principles/filter_rules.md`, `/principles/investing_rules.md` (the non-negotiables, the cash and debt, government customers, earnings evidence, valuation and return math, and news and events rules, and the horizon rules), `/principles/data_rules.md`, `/sources/SOURCES.md` and `/sources/screener.md`, the run's `sector_map.md` entries for the sectors in your batch (`sector_of.tsv`, from `sectors.py order`, gives each company's sector), and earlier decisions in `<run>/gate/b*.json` for calibration.

## Per company (write its file before starting the next)
1. **Data:**
   - The company's row in `<run>/triage.csv` (it holds the screen fields, including "Pledged percentage").
   - Its screener answers in `data/companies/<SYM>/scr/`, fetched with no model tokens by `uvx --from screener-mcp==0.5.0 python scripts/scr_company.py <SYM>` (the orchestrator runs it for the batch; run it yourself for any company it missed; if screener.in can't be reached: `/principles/access_rules.md`):
     - statements (12 years, consolidated and standalone);
     - the last 13 quarters;
     - shareholding for the last 12 quarters;
     - NSE announcements for 3 years, with links;
     - the annual-report and transcript list;
     - insider trades.
   - Promoter holding and pledge per quarter come from `scr/shp_history.json` (the filed shareholding-pattern XBRLs).
2. **Sector:** confirm the company's sector from what it actually does (`scr/overview.json` about text, the business description in the documents you read in step 3). If `sector_of.tsv` has it wrong, record the right sector (an id from `sectors.json`, or "other") and why.
3. **Guidance:** read the latest earnings-call transcript and investor presentation filed in the last 12 months (download from the exchange links in the saved document list or announcements into `data/companies/<SYM>/<FYyyQn>/`, with text via `pdf_text.py`, recorded in `index.json`); if neither exists, the latest annual report's Management Discussion & Analysis or the AGM speech. Record every numeric guidance item with its timeline (revenue growth, margin, profit, capacity and commissioning dates, order book and inflow, capex, debt) and management's explanation for any weak metric. Which guidance counts: the gate standard.
4. **Filings (news check):** go through the last 12 months of the saved announcements (`scr/announcements.json`); open any filing whose title signals governance or a business event and read it. Record governance (auditor resignation/qualification/change with the stated reason, SEBI/ED/tax/GST actions, fraud or forensic audit, defaults or rating downgrades, promoter sales or purchases, pledge creation/release/invocation, preferential issues/QIPs/warrants, KMP or independent-director exits with the reason, related-party approvals, penalties, plant shutdowns, litigation) and business events (order wins with value, capacity commissioning, acquisitions, rating upgrades). When the promoter stake fell 0.5 point or more in the last 2 quarters or a filing shows a promoter sale, also read the insider trades (`scr/insider.json`) and SAST disclosures (`scr/sast.json`, from NSE; BSE for a per-person annexure) and find the reason (the promoter selling and buying rule).
5. **Return math** per horizon, as the gate standard sets it (growth g, exit P/E, dividends, one-offs normalised); say how you chose g and the exit P/E, and whether a dated sector tailwind shows in the company's own filings.
6. **Decide** NEXT or REJECT on the gate standard's line and floors.
7. **Verify before rejecting:** every figure a REJECT rests on is checked against the filed document, per `/principles/data_rules.md`. A NEXT with a promoter fall of 0.5 point or more starts its "why" with "check promoter:".

## Output (python, ensure_ascii=False)
- `<run>/gate/<SYM>.json`: sym, name, sector (confirmed id, and `sector_was` when you changed it, with the reason), data_used {figures and their source}, docs [type, date, url], guidance [..], explanations [..], governance [{date, filing, item}], business [{date, filing, item}], data_conflicts [..], for_s13 [items the full analysis must check], unknowns [..].
- `<run>/gate/bNN.json`: a list, one entry per company: {sym, decision ("NEXT"/"REJECT"), why (one sentence with the deciding numbers), g_used, exit_pe_used, est_cagr (best horizon), horizon, floor_failed (or null), verified_against (document and page, for every REJECT)}.

Reply with one line per company: sym, decision, est_cagr, sector (and whether you changed it), and any integrity flag.
