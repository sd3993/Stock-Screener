# Tools: how to reach each source, the scripts, and the sheet's layout

How to reach each source, and what has already been found about each, so no session re-researches it; no policy. Which sources count and how filings are stored: `process/data_rules.md`. Investing rules: `process/investing_rules.md`. What each phase does: `process/README.md`. Run everything from the project root (PowerShell).

## Where each item comes from (start here)
| Need | Source | How (no model tokens unless noted) |
|---|---|---|
| Whole-market fields, idea screens (P2) | screener screens (MCP, logged in) | `p2_screens.md`; 200-row pages to file, `scr_save.py`, `build_universe.py` |
| Statements: 12 years, 13 quarters, both bases | screener public company page | `scr_company.py` → `scr/profit_loss…quarterly` |
| Shareholding, 12 quarters; promoter % and pledge per quarter | screener page; NSE filed SHP XBRL | `scr_company.py` → `scr/shareholding`, `scr/shp_history` |
| Promoter pledge (latest), SAST Reg 29, corporate actions, SHP list (about 26 quarters) | NSE feeds | `scr_company.py` → `scr/pledge_nse`, `sast`, `corporate_actions`, `shareholding_nse` |
| Announcements with PDF links, 3 years; insider trades | NSE feeds | `scr_company.py` → `scr/announcements`, `insider` |
| Annual reports (back to about 2013), transcripts, credit-rating letters, peers, about text | screener page | `scr_company.py` → `scr/documents`, `credit_ratings`, `peers`, `overview` |
| The documents themselves (results, ARs, transcripts, governance) | exchange PDFs | `scr_docs.py`; text via `pdf_text.py` |
| BSE-only companies, documents NSE lacks | BSE | `bse_fetch.py` + `bse_fetch.js` in the browser pane (below) |
| Long price, P/E, EPS, market cap history (about 2005 onward, incl. merged/delisted) | screener public chart API | `mb_history.py` |
| Stored price for the sheet (P8) | screener page | `scr_company.py --only overview` |
| Tapetide | not needed by any phase | reference only (below) |

## Settled findings (don't re-research; re-check only when something breaks)
- **screener MCP:**
  - Answers over `MAX_MCP_OUTPUT_TOKENS` (3,000 here) go to a file automatically.
  - `screen_stocks` takes `limit` up to 200, and its sort is server-side.
  - A field named in a query drops the rows where it is empty; column-set fields come back as null.
  - Free accounts keep 15 columns.
  - The MCP's per-company tools cut to 8 quarters and 50 announcements; the public page and NSE feeds don't.
  - Company pages are public; only screens need login.
- **screener has no pledge history** (only the current pledge, as a sentence in its cons, when significant). Pledge history is read from NSE's filed SHP XBRLs.
- **BSE's API is bot-protected:** scripts and curl get 403, and working around it (browser headers, cookies or fingerprints faked) isn't allowed. BSE's API is browser-pane only; its PDFs download with plain curl. NSE goes first for NSE-listed companies.
- **Browser pane can't reach local addresses:** a page's request to 127.0.0.1 gets `ERR_BLOCKED_BY_CLIENT`, and bseindia.com's CSP blocks `eval`, so a snippet can't be loaded from a local server. Data leaves the pane only through a tool result: a result over MAX_MCP_OUTPUT_TOKENS is saved to a tool-results file and shown as a short notice (pad small results so they're saved too).
- **BSE announcements API** (`AnnSubCategoryGetData`) sends 50 rows a page and no page count: page until a page adds no new `NEWSID`.
- **NSE:**
  - Feeds work from scripts through the screener-mcp library's session.
  - XBRL files need that session; plain curl gets nothing.
  - Archive PDFs download with curl from `archives.nseindia.com` (not `nsearchives`).
- **Tapetide (trial, 3 Nov 2026):**
  - Filings lists are short (from Dec 2025 for the trial companies).
  - `/financials` mixes bases across companies.
  - Only 136 delisted companies.
  - Data starts around 2015.
  - Free plan, 50 calls a day; the user won't pay.

  Nothing it uniquely offers is needed now.
- **Throughput:** `mb_history.py` manages about 13 companies a minute, and screener rate-limits the browser while it runs (login pages show "Too many requests").

## Scripts (`tools/scripts/`)
Run as `python tools/scripts/<name>.py`. The run folder comes from `config.py` (`RUN`, or the `RUN` environment variable, else the newest `runs/FY*`).
- **screener.in:** `scr_company.py SYM [--only …]` (one company's screener data, no login and no model tokens; run as `uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py SYM`), `scr_save.py` (saves a screener MCP answer to a file, from the app's saved copy or the transcript), `scr_docs.py SYM` (P6: downloads the results filings, annual reports and transcripts listed in the company's saved screener answers, recorded in `index.json`).
- **Tapetide:** `tt.py` (REST client: `usage`, `get <route> k=v [--save PATH] [--all-pages]`, `calls [days]`; caching and call log for every other script), `tt_docs.py` (shared: filings/documents lists, downloads, `index.json`).
- **Task 2 (`studies/multibaggers/`):** `mb_history.py SYM… | --csv FILE` (long price, P/E, EPS, market-cap-to-sales and sales history from screener's public chart API, back to about 2005; run through uvx like `scr_company.py`), `mb_outcomes.py` (price and market-cap multiples per window from those histories → `studies/multibaggers/outcomes.csv`).
- **Phases:** `build_universe.py` (P2 → `universe.csv`), `triage.py` (P3 → `triage.csv`, `gate_batches.json`), `gate_merge.py` (P4R → `gate/decisions.csv`), `facts_check.py SYM` (P6: `facts.json` vs the cached screener and Tapetide figures), `check_pending.py` (after P8: `PENDING: n`).
- **BSE:** `bse_fetch.py job|save` with `bse_fetch.js` (pledge, shareholding, results, corporate actions and announcements for companies NSE doesn't cover, through the browser pane; steps in the script's header).
- **Documents:** `pdf_text.py <pdf> 1 9999 <out.txt>` (PDF → text with page markers). BSE/NSE fallback only: `bse_pdf.py`, `save_b64_pdf.py`, `save_js_file.py`, `save_last_js.py`.

## screener.in MCP (main source; `mcp__screener__*`)
- **Account:** the MCP server logs in with the account the user configured in its settings; never read or use those credentials.
  - The account's column set (screener.in → Edit columns, `/user/columns/`) decides which fields every screen row carries; fields named in a query are added on top.
  - The user allowed changing it for this project (3 Nov 2026). Free accounts keep at most 15 columns (screener silently drops the rest on save). It holds exactly the fields in `process/screens.json` → `columns`; change both together.
  - To change it, use the browser pane, where the account is logged in, at `/user/columns/`: filter, tick or untick, then Save columns. The list's remove buttons re-render after each click, so re-read the page between clicks.
  - After changing it, check one screen row has every listed field.
- **Public mode, for scripts (no login, no model tokens):** `scr_company.py` and `mb_history.py` import the screener-mcp library through `uvx --from screener-mcp==0.5.0 python …`, without credentials.
  - It reads screener's public company pages (all 12 years and 13 quarters, 12 quarters of shareholding, and the credit-rating letters; the MCP tools cut to 8), NSE's feeds (announcements, every row, where the MCP tool caps at 50; insider trades; promoter pledge, latest only; SAST Reg 29; corporate actions; the shareholding-pattern list, about 26 quarters), and the public chart API.
  - NSE feeds query both `index=equities` and `index=sme`, since a company that moved boards has rows under both. The shareholding-pattern XBRLs (`xbrl` link in each quarter's row) are fetched through the library's NSE session; plain curl gets nothing. The promoter-group context `ShareholdingOfPromoterAndPromoterGroup_ContextI` holds the promoter shares and the pledged % of them (`EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares`, a fraction); `ShareholdingPattern_ContextI` holds total shares. In NSE's pledge feed, `percPromoterShares` is the promoter pledge (% of promoter shares); `percSharesPledged` counts every holder.
  - The chart API (`/api/company/<id>/chart/?q=…&days=10000`) gives price and volume, P/E with TTM EPS, and market cap to sales with TTM sales back to about 2005, including merged and delisted companies.
  - Only screens need the logged-in MCP.
- **Paging without inline answers:** a page under about 190 rows comes back inline and costs context. Cover a query of T rows (T ≥ 200) with full 200-row pages only: `sort_by` "Market Capitalization", order desc, pages 1..floor(T/200), then one asc page 1 for the remainder (overlap is fine).
- **Keeping answers out of context:**
  - An answer over the tool-result limit is saved by the app to a file, and the call returns only the path: pass it to `scr_save.py --file`. Nothing enters context. The limit is set to 3,000 tokens for this project (`MAX_MCP_OUTPUT_TOKENS` in `.claude/settings.local.json`, set at the user's request on 3 Nov 2026), so most screens go to file; still ask for big pages (`screen_stocks` `limit` 200). An answer from any MCP tool that must be read goes to a file the same way: read it from the file.
  - A small answer comes inline: save it right away with `scr_save.py --marker <a word in it> --tag <your brief's tag>`.
  - Run `scr_save.py` from the Bash tool: PowerShell splits the `--args` JSON at its inner quotes.
  - Never read a saved file whole into context; scripts read it.
- **`screen_stocks`:**
  - `limit` up to 200 rows. Page N makes the server re-fetch pages 1..N from screener (slow; rate limits), so split a big query into market-cap bands of at most 200 rows rather than paging deep.
  - Always set `min_market_cap` 0 (it otherwise adds a ₹100 cr floor) and `exclude_flagged` false (it otherwise drops odd rows).
  - Rows: `symbol`, `name`, `company_id`, `fundamentals` {field: value}. AND/OR/parentheses run natively; field names are screener's exact ones ("Price to Earning", "Historical PE 5Years").
  - A field in the column set comes back on every row, empty or not. A field used in a condition (`X > -9999999`) drops the companies where it is empty, so whole-market fields belong in the column set, not in the query.
- **Per company:**
  - `get_financials`: `statement` profit_loss / balance_sheet / cash_flow / ratios, `financial_type` consolidated / standalone, `years` ≤12, but only the years on screener's page (KRISHNADEF: 4).
  - `get_quarterly_results`: last 8 quarters.
  - `get_shareholding_pattern`: 8 quarters. Pledge is only a flag; the current % is the screen field "Pledged percentage", and the history is `scr/shp_history.json`.
  - `get_insider_trading`: NSE PIT, `days`.
  - `get_company_announcements`: NSE; `category` results / board_meeting / insider_trading / agm / acquisition / fund_raise / credit_rating / …; `days` ≤3650; at most 50 rows per answer, so use categories and windows.
  - `get_document_list`: annual reports back to about 2013, with BSE links; transcripts, some of them on the company website.
  - `get_bulk_deals` (last 90 days), `get_company_overview`, `get_peer_comparison`.
- **Cache:** `data/companies/<SYM>/scr/<name>.json`, each `{fetched_at (IST), via, tool, args, warnings, partial, data}`. Names: `profit_loss`, `balance_sheet`, `cash_flow`, `ratios` (and `_standalone` versions), `quarterly`, `shareholding`, `insider`, `announcements`, `documents`, `overview`, `peers`, `credit_ratings`, `pledge_nse`, `sast`, `corporate_actions`, `shareholding_nse`, `history` (task 2).
- **Quirks:**
  - Figures are rounded to whole crore.
  - "Public" includes the shareholders Tapetide lists as "Others".
  - Results announcements include newspaper copies: take the "Outcome of Board Meeting" / "Financial Result Updates" filing.
  - The connection can drop mid-run: run ToolSearch again before calling it unavailable.

## Tapetide (REST API; reference only: no phase needs it; free plan 50 calls a day)
- **Access and quota.** REST API only (`CLAUDE.md`, "Tapetide via REST"): `https://api.tapetide.com/v1`, bearer token from `TAPETIDE_TOKEN` (the user creates the personal token, `tpt_rt_…`, at https://tapetide.com/settings/tokens). One call costs one unit; failed calls are refunded. Free plan: 50 a day. Starter plan: 400 a day and 5,000 a month. `python tools/scripts/tt.py usage` shows the position (free route). Scripts save answers without spending model tokens.
- **Downloads are free:** a parsed document's `links` (`pdf_url`, `markdown_url`, page Markdown) on filings.tapetide.com, and the exchange links (`url`) in the filings list (`www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=…`), download with `curl.exe -s -L` and use no quota.
- **Cache:** `data/companies/<SYM>/api/<name>.json`, each `{fetched_at (IST), via, route, params, data}`. Names: `financials` (all sections, all periods), `fundamentals` (`/fundamentals?basis=preferred`, 11 years: the same figures with each row's basis stated), `shareholding`, `pledge`, `pledge_events`, `insider`, `sast`, `deals`, `filings` (3 years), `documents`, `credit_ratings`, `corporate_actions`, `profile` (with peers), `quote`. Market-wide answers go in `data/market/`.
- **Call log:** `data/calls.csv` (ts_ist, via, route, symbol, params, status, run). Scripts (and `tt.py get`) log every call. `python tools/scripts/tt.py calls` prints calls per day.
- **Routes used** (`/v1/stocks/{symbol}/…`; all routes and limits in the OpenAPI spec below): `/financials` (`section` quarterly / profit_loss / balance_sheet / cash_flow / ratios; `periods` up to 40), `/shareholding` (includes the promoter pledge block), `/promoter-pledge`, `/promoter-pledge/events`, `/insider-trades` (transaction types buy/sell/pledge/pledge_release/pledge_invocation/esop), `/sast-disclosures`, `/bulk-block-deals`, `/filings` (`category`: financial_results, annual_report, earnings_call, investor_presentation, credit_rating, capital_raise, insider_takeover, management_change, orders_contracts, acquisition, insolvency, compliance, …; pages up to 200), `/documents`, `/documents/summary`, `/documents/read`, profile `/v1/stocks/{symbol}?include=peers`, `/credit-ratings`, `/corporate-actions`, `/prices/daily`, `/v1/quotes?symbols=` (batch quotes), `/v1/screens/fundamental`, `/v1/screens/fundamental/fields`. Point-in-time fundamentals with a chosen basis: `/fundamentals?basis=consolidated|standalone&as_of=`.
- **Full REST reference:** `https://api.tapetide.com/openapi.json` (free download, no quota): every route, parameter and limit. Run `tt.py` from PowerShell: Git Bash rewrites `/v1/...` into a Windows path (and with `MSYS_NO_PATHCONV=1`, `/c/...` save paths land under `C:\c\...`).
- **History routes** (task 2): `/fundamentals` (tidy rows per metric and period, `basis`, `as_of` point-in-time, `available_from` per row, 1,000 rows a page; in practice from FY2015 for annual and the Mar-2015 quarter for quarterly, though the spec says 1999/2002; revisions kept only from Jul 2026, so earlier `as_of` views carry later restatements), `/prices/daily` (split/bonus-adjusted, from 1996 for old listings, at most 5 years per call, 5,000 rows a page), `/market-cap` (daily, from Aug 2015, 5 years per call; empty for delisted companies), `/reference/stocks?status=delisted|inactive` (master list incl. delisted; only 136 delisted on 3 Nov 2026), `/reference/symbol-history/{symbol}` and `/reference/resolve` (from 2016; merged MINDTREE not found), index membership only from Mar 2026. `/financials` returns only the last 14 quarters but 12 annual years.
- **Filings list** (`/filings`): PDF link in `document_url`, date in `filed_at`. Coverage can be short (KIRLOSBROS: only from Dec 2025): older filings come from BSE/NSE. Parsed documents (`/documents`): annual reports carry `period` "FY2026" and a placeholder `doc_date` (2026-01-01); concall/presentation dates are the 1st of the month.
- **Screener limits:** no arithmetic between ratios (e.g. `> 10 * Market Capitalization 10years back` is a 400); REST `limit` max 50. Longest return field is "Return over 5years"; history fields include "Market Capitalization 3/5/7/10years back", "EPS/Profit growth 10Years", "Historical PE 10Years".
- **Screener** (`/v1/screens/fundamental`): the same query language and ratio names as screener.in ("Price to Earning", "Historical PE 5Years"; exact names, or the query errors). Every queried ratio comes back by its full name in `ratio_values`. "Historical PE 5Years" is a 5-year median.
- **Quirks:** in `get_shareholding`/`get_promoter_pledge`, `pct_of_promoter_holding` is the promoter pledge; `all_holders_pledged_pct_of_demat_shares` (alias `pct_total_shares_pledged`) counts every holder and is not a promoter figure. A bucket moving more than 5 points in one quarter may be a filing reclassification. `/financials` doesn't state its basis and it varies by company (KIRLOSBROS consolidated, KRISHNADEF standalone though it files consolidated): use `fundamentals` (each row has `basis`) and confirm against the results filing. Tapetide's shareholding can differ from the filed pattern (KRISHNADEF Mar 2024: 68.33 vs 61.29): a decisive holding is read from the filing. `available_from` in financials is the declaration date (for look-ahead-free history), but values are the latest restated ones. In `/financials`, "Net Profit" is the profit after the share of JVs and before the non-controlling split (not owners' PAT), "Borrowings" include lease liabilities, and values are ₹ crore (results filings often print ₹ million). Parsed text is Tapetide's own conversion and some documents are mislabelled: read decisive figures from the PDF page. The filings list's `concall_audio` rows are often the transcript filing itself. `get_stock_deals` without a type mixes old bulk deals with insider rows: use the REST `insider-trades` and `sast-disclosures` routes (or `type`) for promoter activity.

## BSE/NSE directly (for what the scripts above don't cover; `process/data_rules.md`)
- **BSE PDFs:** `www.bseindia.com/xml-data/corpfiling/AttachHis/<id>.pdf` (same-day filings often under `AttachLive`) with `curl.exe` and its default identity; `AnnPdfOpen.aspx?Pname=<id>.pdf` is the same file. `bse_pdf.py SYM "regex" files...` downloads and extracts. Some transcript links return an HTML page from both paths: use the NSE copy. Large companies sometimes file only a cover letter linking to a website transcript: read the linked file and say so.
- **BSE APIs** (bot-protected, so scripts can't call them): `bse_fetch.py` and `bse_fetch.js` cover the usual items for a batch of about 20 companies, saved to `data/companies/<SYM>/bse/`. For anything else, call api.bseindia.com with fetch() from a www.bseindia.com tab (CORS allowed): `Integratedfinancedata/w?scripcode=` (iXBRL filings since the Mar-2025 quarter), `ConsolidatePledge/w`, `TabResults_SHP/w` (last 3 quarters), `shpSecSummery_New/w?qtrid=<n>.00&scripcode=` (one quarter's pattern; Sep 2026 = 131), `CorporateAction/w`, `ListofScripData/w` (all scrips: `SCRIP_CD`, `scrip_id` = NSE-style symbol), announcements `AnnSubCategoryGetData/w?pageno=&strCat=-1&strPrevDate=YYYYMMDD&strScrip=<code>&strSearch=P&strToDate=&strType=C&subcategory=-1` (12-month window).
- **NSE PDFs:** curl to nsearchives.nseindia.com hangs; the same paths download from `https://archives.nseindia.com/corporate/...` (`curl.exe -s -m 60 -o <file> <url>`). Fallback: fetch as base64 inside an nsearchives tab and decode with `save_b64_pdf.py`.
- **NSE APIs** (scripts reach them through the screener-mcp library's NSE session, as `scr_company.py` does; otherwise from a www.nseindia.com tab): `/api/integrated-filing-results` (also `index=sme`), `/api/corporate-share-holdings-master`, `/api/corporates-pit?index=equities|sme&symbol=&from_date=&to_date=` (insider trades, pledges), `/api/corporate-announcements?index=equities&symbol=&from_date=&to_date=`. `corporate-announcements` silently drops rows over wide windows: query one month at a time.
- **Promoter sales:** when the insider (PIT) feed and the SAST Reg 29(2) disclosure disagree on size, read the Reg 29(2) per-person annexure first (it covers everyone acting in concert). Settle promoter-group membership from Reg 31(4) declarations and the shareholding pattern's promoter list. A fall in promoter share count with unchanged total shares means a sale, transfer out or reclassification.
- **Scanned PDFs** give no text (no OCR here); render pages as images and read them, and say so. Extract page images with pypdf's `page.images` (Pillow); image-mask pages that won't render are read from the OCR text layer and checked by arithmetic. Mixed-raster SAST PDFs: wrap each layer's raw stream (pypdf) in a TIFF header, convert to PNG (.NET System.Drawing) and read the image.
- **Browser pane:** WebFetch can't open nseindia.com or bseindia.com; don't spoof a browser. Each helper opens one tab of its own, passes its tabId on every call and closes it when done. `javascript_tool` times out at 45 s: start long work un-awaited and poll; save large results with `save_js_file.py`. Never wait on a script or download more than about a minute: reload and retry up to three times, then report the company as unfinished.
- **XBRL quirks:** owners'-share PAT tags are sometimes 0 or wrong for a single quarter (cross-check the results PDF); some filers tag income tax paid under investing.

## Zerodha Kite MCP
`get_holdings`, `login`. Sessions expire; ask the user to log in, with the warning in `CLAUDE.md`.

## Google Sheets MCP
`get_values`, `update_values`, `update_formulas`, `update_spreadsheet` (copyPaste for formats, conditional formatting), `batch_clear_values`; parameter `spreadsheetId`. Old verdicts (before 23 Oct 2026) are in the Drive copy "Stock Screener (archive, old verdicts as of 23 Oct 2026)".

## The sheet (built 24 Oct 2026; `1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU`)
Final outcomes only, light colours only, related columns merged to limit horizontal scrolling.
- **Tabs and sheetIds:** Short term 101, Medium term 102, Long term 103, Allocation 7, Holdings 104, Pending results 105 (renamed each quarter; its name is in Data!BA1), Data 106, Data Flags 10. Formulas are pre-filled (Data rows 2-300, bucket tabs 2-200, Holdings/Allocation 2-100). Which columns each phase writes: `process/p8_listing.md` (Data, Data Flags, Pending) and `process/p9_allocation.md` (Holdings, Allocation); every other column is a formula and is never written.
- **Data:** one row per analysed company. Formula columns AD:AZ and BD: live price chain, P/E now, forward P/E, PEG, multiples and CAGR per bucket (base multiple = horizon-end base EPS × exit P/E + dividends, ÷ live price; CAGR over 2/5/7 years), bear multiples, short-term target price and % to target, re-rating share, pending flag, data-flag flag, held flag. BA1 holds the pending tab's name.
- **Bucket tabs:** live formula views of Data (hidden column Z is the sorted ticker list), sorted by expected CAGR, descending. A company is listed when P7 made it eligible for that bucket (nested: long ⇒ medium ⇒ short) and its non-negotiables aren't Fail; a holding is always listed (its closest bucket if eligible for none). Price moves never remove a row: when the live price breaks a rule (CAGR < 25%, bear < 0.8x, forward P/E ≥ 50 or negative, PEG > 2 or negative), or the company fails a non-negotiable or isn't eligible (holdings), the row's text turns red and "Below rule (live)" lists every reason. Short term also has target price, % to target and a sell-trigger cell; medium and long show exit P/E and re-rating share. Each row links to the company's other bucket tabs.
- **Allocation:** P9's actions with live price, current value and bucket links; P1:S4 shows each bucket's share of target and current value against its range, a multi-bucket position counted equally in each bucket. The range text in Q2:Q4 copies rule 18 of `process/investing_rules.md`; update it whenever that rule changes.
- **Holdings:** P9's status per holding with live price, value, P&L and bucket links.
- **Live price chain:** GOOGLEFINANCE (`NSE:SYM` or `BOM:<code>`); if N/A, screener.in's price via IMPORTXML from the "Screener URL" column (a sheet formula, not a research source); if that fails too, the stored price from the last P8.
- **Colours, one meaning each** (a cell colour overrides the row colour on that cell; red text combines with any fill): row light yellow = results pending; ticker cell light red = data flag (links to the company's first row in Data Flags); price cell light orange = screener price, light grey = stored price; sell-trigger cell light green = short-term target hit; Holdings Qty and Avg-cost cells light blue = Kite didn't refresh; red text = a rule broken (reasons in "Below rule (live)").

## Local
- Python 3.13 with `pypdf`, `openpyxl` and `Pillow` (installed 3 Nov 2026, so `page.images` works on scanned PDFs); `curl.exe` for downloads.

## Workflows (only if the user asks for one)
- Don't resume a multi-lane script with `resumeFromRunId` (the cached prefix breaks at the first failed agent); list what's done from the files and relaunch with only what's left.
