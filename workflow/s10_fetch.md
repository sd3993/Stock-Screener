# S12.0: fetch subagent, one company (standard tier; the orchestrator runs the fetch scripts first, S10; both modes)

You fetch and store everything the analysis of one company will need, extract its key figures accurately, and report what changed. No analysis, opinions or verdicts; copy figures exactly from the documents. Working directory: the project root (PowerShell; never cd elsewhere). The company, the run quarter (`FYyyQn`) and whether the fetch scripts already ran are in your brief.

1. Read `/principles/data_rules.md`, `/workflow/fetch_learnings.md` (known quirks; apply them) and `/sources/screener.md` and `/sources/exchanges.md`.
2. **Data** (skip what's cached and current per `/principles/data_rules.md`). The orchestrator has already run the two fetch scripts (S10), in this order. Check their printed summaries against this list and fill any gap (`/sources/SOURCES.md`; if screener.in can't be reached: `/sources/screener.md`):
   - `uvx --from screener-mcp==0.5.0 python scripts/scr_company.py <SYM>` puts the company's screener answers in `data/companies/<SYM>/scr/`, with no model tokens:
     - statements, 12 years, consolidated and standalone;
     - every quarter on screener's page (13);
     - shareholding for 12 quarters;
     - peers;
     - the annual-report and transcript list;
     - NSE announcements for 3 years, with links;
     - insider trades;
     - NSE's pledge, SAST, corporate-action and shareholding-pattern feeds, and promoter holding and pledge per quarter from the filed shareholding-pattern XBRLs (`scr/shp_history.json`; use it for the shareholding figures in step 4);
     - credit-rating letters.
   - `python scripts/scr_docs.py <SYM>` downloads the documents those lists point to (step 3).
3. **Documents** into `data/companies/<SYM>/<FYyyQn>/`: the exchange PDF with text via `python scripts/pdf_text.py <pdf> 1 9999 <pdf>.txt`:
   - annual reports for the last 3 years;
   - results filings for the last 6 quarters (half-yearly filers such as many SME companies: the last 4 half-years), plus the half-year results that carry the half-year cash flow and balance sheet. Older periods restated in a later filing (e.g. a move to Ind AS) are recorded both as filed and as restated;
   - the last 6 earnings-call transcripts and last 4 investor presentations; the latest AGM proceedings or chairman's speech;
   - for the last 3 years, from the announcements: auditor appointment/resignation letters, preferential issue / QIP / warrant documents, SAST and insider (Reg 7/29/31) disclosures including pledge creation/release/invocation, credit-rating letters, SEBI/tax/litigation disclosures, related-party approvals;
   - listed under 3 years: the prospectus/RHP.
   What the sources lack, fetch from BSE/NSE per `/principles/data_rules.md` and record why. Check in particular:
   - **BSE-only companies:** the NSE announcements are empty. List the announcements from BSE (`/sources/exchanges.md`, one 12-month window per call) and fetch the results and governance filings above from them.
   - **Transcripts on the company website:** a transcript in screener's list that links to the company website (`scr_docs.py` prints these as skipped) is fetched from the exchange filing of that date ("Analysts/Institutional Investor Meet"); when the website copy may be used: `/principles/data_rules.md`.
4. **facts.json** in `data/companies/<SYM>/`, rebuilt only when new results, annual or shareholding filings arrived. Each figure as {value, unit, basis (consolidated/standalone), period, document, page}, in ₹ crore unless stated, using screener's period labels ("Jun 2026", "Mar 2026"), laid out as {"quarterly": {...}, "annual": {...}, "half_years": {...}, "shareholding": {...}, "shares": {...}, "order_book_guidance": [...]}; "pat" = net profit after exceptional items, owners' PAT as "pat_owners". Figures come from the filed documents:
   - quarterly (last 6): revenue, EBITDA if stated, exceptional items, PBT, tax, PAT, owners' PAT, EPS;
   - annual (last 5 years; the last 3 from annual reports, older ones from screener if no filing is at hand, marked so): revenue, PAT, owners' PAT, CFO, income tax paid and where it sits, capex, borrowings (excluding leases) and lease liabilities, cash and bank incl. deposits and liquid investments, equity, current assets, current liabilities, receivables, inventory, payables, contingent liabilities;
   - half-years (latest two, and H2 = full year minus H1): CFO, receivables, inventory;
   - shareholding (last 12 quarters), keys `promoter_pct`, `pledged_pct_of_promoter`, `total_shares`;
   - share count now and 3 years ago; corporate actions (bonus/split) with dates;
   - order book and guidance numbers only as quoted, with document and date.
   Scanned results PDFs with an OCR text layer can garble digits and columns: read such a quarter from the page image, or rebuild it from a later filing's comparative column, and check it by arithmetic (income − expenses = PBT, PBT − tax = PAT, EPS × shares). State EBITDA's definition when a presentation includes other income.
5. Run `python scripts/facts_check.py <SYM>` (compares `facts.json` with the cached screener figures; writes `facts_check.json`). For each mismatch above 2%, re-read the document once; correct your figure if you misread it, otherwise leave both values.
6. **index.json** in `data/companies/<SYM>/` (you fill the identifiers, confirm `basis` and set `latest_declared_quarter`): {sym, name, nse_symbol, bse_code, sector_screener, basis (consolidated/standalone, confirmed against the results filing), latest_declared_quarter (FYyyQn), last_fetched (date), files: [{file (path relative to the folder), quarter, type, period, filed_date, source ("bse"/"nse"/"web"), doc_id or exchange_id, source_url, sha256, text_file, scanned}], missing: [{what, tried}], fetched_direct: [{what, exchange, why}]}.
7. Append anything new you had to work around to `/workflow/fetch_learnings.md` (re-read it just before writing; one line per item; no duplicates).

8. **Recheck mode:** your brief may name markers to verify (a figure near its line, or a manual marker due): read each from the filed document and record it in `facts.json` under `marker_inputs` ({marker id: {value, unit, period, document, page}}, plus `met`: true/false for an event or a yes/no manual marker); keep `marker_inputs` when `facts.json` is rebuilt.

Reply with exactly: `CHANGED: yes|no` (yes if any new results, annual report, shareholding, transcript, presentation or governance filing arrived, or this is the company's first fetch), `LATEST_DECLARED: <FYyyQn>`, files added, facts_check mismatches left, and what is missing.
