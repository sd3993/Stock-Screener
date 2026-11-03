# P4: gate, one batch (Opus medium)

Decide NEXT or REJECT for each company in your batch, from its figures, its latest guidance and its last 12 months of exchange filings. The gate is a filter: it removes companies that clearly can't meet the rules, and keeps borderline ones for the full analysis (P7). Do not edit any existing file except a company's `index.json` when you download a filing. Working directory: the project root (PowerShell). Your brief gives the run folder, the batch number and whether the data was pre-fetched by script.

## Read first
`process/investing_rules.md` (rules 1, 4, 5, 6, 8, 16 and the buckets section), `process/data_rules.md`, the top two sections and the "screener.in" section of `tools/tools.md`, and earlier decisions in `<run>/gate/b*.json` for calibration.

## Per company (write its file before starting the next)
1. **Data:**
   - The company's row in `<run>/triage.csv` (it holds the screen fields, including "Pledged percentage").
   - Its screener answers in `data/companies/<SYM>/scr/`, fetched with no model tokens by `uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM>` (the orchestrator runs it for the batch; run it yourself for any company it missed):
     - statements (12 years, consolidated and standalone);
     - the last 13 quarters;
     - shareholding for the last 12 quarters;
     - NSE announcements for 3 years, with links;
     - the annual-report and transcript list;
     - insider trades.
   - Promoter holding and pledge per quarter come from `scr/shp_history.json` (the filed shareholding-pattern XBRLs).
2. **Guidance:** read the latest earnings-call transcript and investor presentation filed in the last 12 months (download from the exchange links in the saved document list or announcements into `data/companies/<SYM>/<FYyyQn>/`, with text via `pdf_text.py`, recorded in `index.json`); if neither exists, the latest annual report's Management Discussion & Analysis or the AGM speech. Record every numeric guidance item with its timeline (revenue growth, margin, profit, capacity and commissioning dates, order book and inflow, capex, debt) and management's explanation for any weak metric. Guidance from another company's document or older than 12 months counts as absent.
3. **Filings (news check):** go through the last 12 months of the saved announcements (`scr/announcements.json`); open any filing whose title signals governance or a business event and read it. Record governance (auditor resignation/qualification/change with the stated reason, SEBI/ED/tax/GST actions, fraud or forensic audit, defaults or rating downgrades, promoter sales or purchases, pledge creation/release/invocation, preferential issues/QIPs/warrants, KMP or independent-director exits with the reason, related-party approvals, penalties, plant shutdowns, litigation) and business events (order wins with value, capacity commissioning, acquisitions, rating upgrades). When the promoter stake fell 0.5 point or more in the last 2 quarters or a filing shows a promoter sale, also read the insider trades (`scr/insider.json`) and SAST disclosures (`scr/sast.json`, from NSE; BSE for a per-person annexure) and find the reason (rule 1.2).
4. **Return math** per bucket at base-case EPS growth g: multiple ≈ (1+g)^years × exit P/E ÷ P/E now + years × dividend yield, years = 2 (short), 5 (medium), 7 (long). g = management's numeric guidance where given (profit growth implied by revenue and margin guidance), haircut where its record of delivery is poor, else the sustained 3-year record tempered by the latest two quarters; never the latest quarter's spike. Exit P/E: the own 5-year median P/E capped at 30, judged lower when that history is inflated by depressed past earnings, too short (listed under ~2 years) or the business is cyclical at a peak (use mid-cycle); say so. Normalise one-offs before any P/E.
5. **Decide.** NEXT when the best bucket's base-case CAGR (multiple^(1/years) − 1) is about 22% or more (rougher than the 25% hurdle, so borderline cases reach P7) and no floor fails. Otherwise REJECT. Floors (any one fails → REJECT): cash conversion below rule 1's floor (CFO negative in both latest half-years fails); net debt/equity above 0.8 (lenders: rule 4's lender note instead); pledge per rule 1.1; promoter selling that fails rule 1.2's tests; integrity flags (rule 1.3); holding/investment companies; a one-quarter profit spike off a tiny base with no guidance.
6. **Verify before rejecting:** every figure a REJECT rests on is checked against the filed document (results filing, annual report or shareholding pattern), per `process/data_rules.md`. A NEXT with a promoter fall of 0.5 point or more starts its "why" with "check promoter:".

## Output (python, ensure_ascii=False)
- `<run>/gate/<SYM>.json`: sym, name, data_used {figures and their source}, docs [type, date, url], guidance [..], explanations [..], governance [{date, filing, item}], business [{date, filing, item}], data_conflicts [..], for_p7 [items the full analysis must check], unknowns [..].
- `<run>/gate/bNN.json`: a list, one entry per company: {sym, decision ("NEXT"/"REJECT"), why (one sentence with the deciding numbers), g_used, exit_pe_used, est_cagr (best bucket), bucket, floor_failed (or null), verified_against (document and page, for every REJECT)}.

Reply with one line per company: sym, decision, est_cagr, and any integrity flag.
