# Data rules (read by every phase that fetches or uses figures: P2-P7)

How to reach each source (routes, scripts, quirks) is in `tools/tools.md`. This file says which sources count and how to treat them.

## Sources
- **screener.in (its MCP) is the main source:**
  - figures: annual statements (up to 12 years), the last 8 quarters, ratios, screens;
  - shareholding (8 quarters) with screener's pledge flag;
  - insider trades (NSE PIT feeds) and NSE bulk deals;
  - announcements (NSE, up to 10 years back, with the exchange PDF link);
  - the list of annual reports and call transcripts (exchange links, back to about 2013).

  Ask for consolidated or standalone explicitly (`financial_type`).
- **NSE's own feeds** (read by `scr_company.py` through the screener library) add:
  - promoter pledge (latest);
  - SAST Reg 29 disclosures;
  - corporate actions;
  - the shareholding-pattern list (about 26 quarters);
  - promoter holding and pledge per quarter, read from the filed shareholding-pattern XBRLs (last 12 quarters).

  screener's company page lists the credit-rating letters.
- **Tapetide (REST, free plan, 50 calls a day)** is no longer needed by any phase. Use it only for something specific neither screener nor the exchanges have, and say what.
- **Filed documents are ground truth.** A figure that decides an outcome (a reject, a non-negotiable, an EPS path, a data flag) is checked against the filed document itself: the results filing, annual report or shareholding pattern.
  - Get the document from the exchange link that screener's lists or Tapetide give.
  - On a mismatch, rule out definition gaps first: standalone vs consolidated, restatements, bonus/split, one-offs, TTM vs FY, units, rounding to whole crore.
  - Then use the filing, record both values as a data flag, and re-check the source's other figures for the company.
- **Basis:** use consolidated figures where the company files them, standalone otherwise, and say which. Confirm against the results filing on a company's first fetch and record it in `index.json`.
- **BSE/NSE directly** for what neither source has:
  - a filing missing from both lists;
  - shareholding patterns older than screener's 8 quarters;
  - an unreadable document;
  - an SME company not covered;
  - a SAST per-person annexure;
  - a figure that needs the exchange's XBRL.

  Say what was missing and why in the company's `index.json` (`missing` and `fetched_direct`) and in `process/fetch_learnings.md`. NSE first for a company listed there, since its feeds and archives work from scripts. BSE (browser pane) for BSE-only companies, or when NSE lacks the document or it's unreadable there. Record which exchange each file came from.
- **Which document:** take every document from the exchange filing, not the company website or a third party. Use those only when the exchange has no copy (or the filing itself links to it), say so, and note it in unknowns. screener's transcript list sometimes points to the company website: look for the exchange copy first. Rank by assurance:
  - audited annual figures;
  - limited-reviewed quarterly/half-year figures;
  - unaudited statutory disclosures (shareholding, pledge, SAST/insider);
  - presentations and call transcripts (guidance and explanations only, never figures that override results).
- **Guidance and news** come only from exchange disclosures, never from news sites, blogs, broker notes, analyst estimates or other websites. These are pointers only; every number or claim used is read in the filed document itself:
  - screener's AI and research tools (`ask_company_research`, `notebook_ai`, `get_forward_outlook`, `analyze_red_flags`, `get_moat_signals`, `get_recent_news`, `get_analyst_targets`);
  - Tapetide's digests, news, forecasts and score.
- **Known quirks of each source:** `tools/tools.md`.

## Calls and caching
- **Every answer is saved:** screener answers in `data/companies/<SYM>/scr/` (market-wide ones in the run folder or `data/market/`) with `python tools/scripts/scr_save.py`; Tapetide answers in `data/companies/<SYM>/api/`, each Tapetide call logged (`tools/tools.md`).
- Read the cache before calling. Call again only when the data may have changed since (new results, shareholding or filings since the fetch date) or when a doubt needs a fresh copy.
- Downloads from document links (exchange PDFs, `filings.tapetide.com`) are free.

## Storing company data (`data/companies/<SYM>/`)
- One folder per company holds everything about it, whatever the source: documents in quarter folders, screener answers in `scr/`, Tapetide answers in `api/`, and `index.json`, `facts.json`, `facts_check.json`, `search_log.json` at the top.
- Documents go in quarter subfolders `<FYyyQn>/` (year first, e.g. `FY27Q1`): a quarter's results, call transcript, presentation and shareholding together; an annual report under that year's Q4 (AR FY26 → `FY26Q4`); ad-hoc announcements by the quarter of their filing date. `index.json`, `facts.json` and `facts_check.json` stay in `data/companies/<SYM>/` itself. Files left loose by earlier sessions are moved into their quarter subfolder.
- **No re-downloads:** `index.json` records the company's latest declared quarter, last fetch date and, for every file, its source (Tapetide doc_id or exchange attachment ID), source URL and SHA-256. List the company's filings first and download only what isn't in the index; if a new file has the same SHA-256 as one already held, record it but keep no second copy. Prefer Tapetide's Markdown (`.md`) for reading and keep the PDF for figures that decide outcomes. A repeat fetch with nothing new downloads nothing. Every phase that downloads records the file in `index.json` (creating it if missing); P6 also indexes any file in the folder that isn't in `index.json` yet.
- **Missing documents** listed in `index.json` are searched for again on every fetch.
- **Superseded documents:** when the company re-files a document (revised results, a corrigendum, a re-filed shareholding pattern or transcript), rename the old file and its text with the suffix `_superseded` before the extension and update its name in `index.json`. No phase reads superseded files.
- **Individual figures** need no marking: `facts.json` keeps one value per figure, the highest-assurance one (audited over limited-reviewed), the latest filed among equals, with its source document and page.
- Never delete downloads; only the user decides that, if space runs out.
