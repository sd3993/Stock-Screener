# Data rules

Which sources count and how to treat them. What each source offers, how to reach it and its quirks: `/sources/SOURCES.md`.

## Sources
- **screener.in is the main source** (through the screener scripts, which also read NSE's feeds). Ask for consolidated or standalone explicitly (`financial_type`).
- **Filed documents are ground truth.** A figure that decides an outcome (a reject, a non-negotiable, an EPS path, a data flag) is checked against the filed document itself: the results filing, annual report or shareholding pattern.
  - Get the document from the exchange link in screener's lists.
  - On a mismatch, rule out definition gaps first: standalone vs consolidated, restatements, bonus/split, one-offs, TTM vs FY, units, rounding to whole crore.
  - Then use the filing, record both values as a data flag, and re-check the source's other figures for the company.
- **Basis:** use consolidated figures where the company files them, standalone otherwise, and say which. Confirm against the results filing on a company's first fetch and record it in `index.json`.
- **BSE/NSE directly** for what the screener scripts don't give:
  - a filing missing from their lists;
  - shareholding patterns older than screener's 12 quarters;
  - an unreadable document;
  - an SME company not covered;
  - a SAST per-person annexure;
  - a figure that needs the exchange's XBRL.

  Say what was missing and why in the company's `index.json` (`missing` and `fetched_direct`) and in `/workflow/fetch_learnings.md`. NSE first for a company listed there, since its feeds and archives work from scripts. BSE (in a browser; `bse_fetch.py`, `/sources/exchanges.md`) for BSE-only companies, or when NSE lacks the document or it's unreadable there. Record which exchange each file came from.
- **Which document:** take every document from the exchange filing, not the company website or a third party. Use those only when the exchange has no copy (or the filing itself links to it), say so, and note it in unknowns. screener's transcript list sometimes points to the company website: look for the exchange copy first. Rank by assurance:
  - audited annual figures;
  - limited-reviewed quarterly/half-year figures;
  - unaudited statutory disclosures (shareholding, pledge, SAST/insider);
  - presentations and call transcripts (guidance and explanations only, never figures that override results).
- **Evidence quality** (High / Medium / Low, graded in each analysis): filed orders and running capacity rank above guidance, guidance above extrapolation.
- **Guidance and news:** only from exchange disclosures (the news and events rule); blogs, broker notes, analyst estimates and other websites count as news sites. screener's AI and research tools (`ask_company_research`, `notebook_ai`, `get_forward_outlook`, `analyze_red_flags`, `get_moat_signals`, `get_recent_news`, `get_analyst_targets`) are pointers only: every number or claim used is read in the filed document itself.
- **Figures only from the report** (annual-report statements read by subagents, `/workflow/ar_statements.md`): Every value you write is read from the report's own statement pages (or the schedule/note the statement points to), or is plain arithmetic on figures printed there (say which). Never estimate, never take a figure from memory, another source, a later report or screener. If a field is not printed and can't be computed from printed figures, write `null` and say why in `notes`.

## Calls and caching
- **Every answer is saved:** screener answers in `data/companies/<SYM>/scr/` (market-wide ones in the run folder or `data/market/`), written by `scr_company.py` and `scr_tool.py`.
- Read the cache before calling. Call again only when the data may have changed since (new results, shareholding or filings since the fetch date) or when a doubt needs a fresh copy.
- Downloads from document links (exchange PDFs) are free.

## Storing company data (`data/companies/<SYM>/`)
- One folder per company holds everything about it, whatever the source (layout: `/workflow/WORKFLOW.md`).
- **Full downloads** (S12) only for companies on `company_list.csv`; earlier steps download only the documents they read.
- Documents go in quarter subfolders `<FYyyQn>/` (year first, e.g. `FY27Q1`): a quarter's results, call transcript, presentation and shareholding together; an annual report under that year's Q4 (AR FY26 → `FY26Q4`); ad-hoc announcements by the quarter of their filing date. Files left loose by earlier sessions are moved into their quarter subfolder.
- **No re-downloads:** `index.json` records the company's latest declared quarter, last fetch date and, for every file, its source (exchange attachment ID), source URL and SHA-256. List the company's filings first and download only what isn't in the index; if a new file has the same SHA-256 as one already held, record it but keep no second copy. A repeat fetch with nothing new downloads nothing. Every phase that downloads records the file in `index.json` (creating it if missing); S12 also indexes any file in the folder that isn't in `index.json` yet.
- **Missing documents** listed in `index.json` are searched for again on every fetch.
- **Superseded documents:** when the company re-files a document (revised results, a corrigendum, a re-filed shareholding pattern or transcript), rename the old file and its text with the suffix `_superseded` before the extension and update its name in `index.json`. No phase reads superseded files.
- **Individual figures** need no marking: `facts.json` keeps one value per figure, the highest-assurance one (audited over limited-reviewed), the latest filed among equals, with its source document and page.
- Never delete downloads; only the user decides that, if space runs out.
