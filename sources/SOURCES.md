# Sources index

How to reach each source, and what has already been found about each, so no session re-researches it; no policy. Which sources count and how filings are stored: `/principles/data_rules.md`. Investing rules: `/principles/investing_rules.md`. What each step does: `/workflow/WORKFLOW.md`. Scripts: `/scripts/SCRIPTS.md`.

## Where each item comes from (start here)
| Need | Source | How (no model tokens unless noted) |
|---|---|---|
| Whole-market fields, idea screens (S2) | screener screens (logged in) | `/workflow/s2_screens.md`; `screens.py run` (through `scr_tool.py`'s call, logged in), 200-row pages to file; `screens.py build` |
| Statements: 12 years, 13 quarters, both bases | screener public company page | `scr_company.py` → `scr/profit_loss…quarterly` |
| Shareholding, 12 quarters; promoter % and pledge per quarter | screener page; NSE filed SHP XBRL | `scr_company.py` → `scr/shareholding`, `scr/shp_history` |
| Promoter pledge (latest), SAST Reg 29, corporate actions, SHP list (about 26 quarters) | NSE feeds | `scr_company.py` → `scr/pledge_nse`, `sast`, `corporate_actions`, `shareholding_nse` |
| Announcements with PDF links, 3 years; insider trades | NSE feeds | `scr_company.py` → `scr/announcements`, `insider` |
| Annual reports (back to about 2013), transcripts, credit-rating letters, peers, about text | screener page | `scr_company.py` → `scr/documents`, `credit_ratings`, `peers`, `overview` |
| The documents themselves (results, ARs, transcripts, governance) | exchange PDFs | `scr_docs.py`; text via `pdf_text.py` |
| BSE-only companies, documents NSE lacks | BSE | `bse_fetch.py` + `bse_fetch.js` in a browser (`/sources/exchanges.md`) |
| Long price, P/E, EPS, market cap history (about 2005 onward, incl. merged/delisted) | screener public chart API | `mb_history.py` |
| Stored price for the sheet (S14) | screener page | `scr_company.py --only overview` |

## Source references

- [`screener.md`](screener.md) — Main data source: access modes, query conventions and cached answers.
- [`exchanges.md`](exchanges.md) — Direct exchange access (NSE, BSE) for filings and history the main source lacks.
- [`kite.md`](kite.md) — Brokerage account access for holdings, read-only.
- [`sheet.md`](sheet.md) — The outcome store: spreadsheet access, layout and write ownership.
- [`ar_statements.md`](ar_statements.md) — Old annual reports as a source of statements older than the main source covers.
- [`tapetide.md`](tapetide.md) — Usage reference for the Tapetide API, for manual use at the user's request.
