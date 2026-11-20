# Sources index

How to reach each source, and what has already been found about each, so no session re-researches it, with each source's own access rules. Which sources count: `/principles/data_rules.md`.

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
| Stored price for the sheet (S12) | screener page | `scr_company.py --only overview` |
| Official sector evidence (S5): policy releases, budget lines, sector statistics | PIB, ministries, CEA, indiabudget.gov.in | pib.gov.in refuses plain web fetchers (403): read it in the browser pane; CEA's 2026 transmission PDFs return 404, and the same tables are in PIB's Parliament answers; indiabudget.gov.in demand notes (`sbeNN.pdf`) download directly Parliament answers: the Parliament library (eparlib) refuses curl and fails in the browser; committee reports on sansad.in and ministry-hosted answer PDFs download with curl; pmindia.gov.in opens in the browser pane. |

## Source references

- [`screener.md`](screener.md) — Main data source: access modes, query conventions and cached answers.
- [`exchanges.md`](exchanges.md) — Direct exchange access (NSE, BSE) for filings and history the main source lacks.
- [`kite.md`](kite.md) — Brokerage account access for holdings, read-only.
- [`sheet.md`](sheet.md) — The outcome store: spreadsheet access, layout and write ownership.
