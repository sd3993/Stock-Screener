# P6: fetch one company (Sonnet medium; the orchestrator runs the fetch script first when there's a token)

You fetch and store everything the analysis of one company will need, extract its key figures accurately, and report what changed. No analysis, opinions or verdicts; copy figures exactly from the documents. Do not call any mcp__hearthbot__ tools. Working directory: the project root (PowerShell; never cd elsewhere). The company, the run quarter (`FYyyQn`) and whether `tt_company.py` already ran are in your brief.

1. Read `process/data_rules.md`, `process/fetch_learnings.md` (known quirks; apply them) and the "Tapetide" and "BSE/NSE fallback" sections of `tools/tools.md`.
2. **Tapetide data** into `data/companies/<SYM>/api/` (skip what's cached and current per `process/data_rules.md`). With a token, `python tools/scripts/tt_company.py <SYM>` has already done this and the downloads in step 3; check its printed summary and fill any gap. Without a token, call each with the MCP tools and save it (`tools/tools.md`):
   - financials: each section in full (`quarterly`, `profit_loss`, `balance_sheet`, `cash_flow`, `ratios`);
   - shareholding (quarterly) with pledge; promoter pledge events; insider trades and SAST disclosures (3 years); bulk/block deals;
   - filings list for 3 years (all pages); documents list (parsed transcripts, annual reports, presentations);
   - company profile with peers; credit ratings; corporate actions.
3. **Documents** into `data/companies/<SYM>/<FYyyQn>/`, Markdown from Tapetide's document links where it exists (PDF too for results and annual reports), else the PDF from the filing's exchange link with text via `python tools/scripts/pdf_text.py <pdf> 1 9999 <pdf>.txt`:
   - annual reports for the last 3 years;
   - results filings for the last 6 quarters, plus the half-year results that carry the half-year cash flow and balance sheet;
   - the last 6 earnings-call transcripts and last 4 investor presentations; the latest AGM proceedings or chairman's speech;
   - for the last 3 years, from the filings list: auditor appointment/resignation letters, preferential issue / QIP / warrant documents, SAST and insider (Reg 7/29/31) disclosures including pledge creation/release/invocation, credit-rating letters, SEBI/tax/litigation disclosures, related-party approvals;
   - listed under 3 years: the prospectus/RHP.
   What Tapetide lacks, fetch from BSE/NSE per `process/data_rules.md` and record why.
4. **facts.json** in `data/companies/<SYM>/`, rebuilt only when new results, annual or shareholding filings arrived. Each figure as {value, unit, basis (consolidated/standalone), period, document, page}, in ₹ crore unless stated, using Tapetide's period labels ("Jun 2026", "Mar 2026"), laid out as {"quarterly": {...}, "annual": {...}, "half_years": {...}, "shareholding": {...}, "shares": {...}, "order_book_guidance": [...]}; "pat" = net profit after exceptional items, owners' PAT as "pat_owners". Figures come from the filed documents:
   - quarterly (last 6): revenue, EBITDA if stated, exceptional items, PBT, tax, PAT, owners' PAT, EPS;
   - annual (last 5 years; the last 3 from annual reports, older ones from Tapetide if no filing is at hand, marked so): revenue, PAT, owners' PAT, CFO, income tax paid and where it sits, capex, borrowings (excluding leases) and lease liabilities, cash and bank incl. deposits and liquid investments, equity, current assets, current liabilities, receivables, inventory, payables, contingent liabilities;
   - half-years (latest two, and H2 = full year minus H1): CFO, receivables, inventory;
   - shareholding (last 12 quarters), keys `promoter_pct`, `pledged_pct_of_promoter`, `total_shares`;
   - share count now and 3 years ago; corporate actions (bonus/split) with dates;
   - order book and guidance numbers only as quoted, with document and date.
5. Run `python tools/scripts/facts_check.py <SYM>` (compares `facts.json` with Tapetide's cached financials and shareholding; writes `facts_check.json`). For each mismatch above 2%, re-read the document once; correct your figure if you misread it, otherwise leave both values.
6. **index.json** in `data/companies/<SYM>/`: {sym, name, nse_symbol, bse_code, sector_tapetide, basis (consolidated/standalone, confirmed against the results filing), latest_declared_quarter (FYyyQn), last_fetched (date), files: [{file (path relative to the folder), quarter, type, period, filed_date, source ("tapetide"/"bse"/"nse"), doc_id or exchange_id, source_url, sha256, text_file, scanned}], missing: [{what, tried}], fetched_direct: [{what, exchange, why}]}.
7. Append anything new you had to work around to `process/fetch_learnings.md` (re-read it just before writing; one line per item; no duplicates).

Reply with exactly: `CHANGED: yes|no` (yes if any new results, annual report, shareholding, transcript, presentation or governance filing arrived, or this is the company's first fetch), `LATEST_DECLARED: <FYyyQn>`, files added, facts_check mismatches left, what is missing, and Tapetide calls used.
