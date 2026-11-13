# Scripts index

Single entry point for the deterministic scripts under `scripts/`: which script to use in which situation, and the step that calls it. Each script's `--help` (`python -I scripts/<name>.py --help`) holds its flags, command line, outputs, resume behaviour and checks before re-running.

## Running scripts

- Run as `python scripts/<name>.py`. The run folder comes from `config.py` (`RUN`, or the `RUN` environment variable, else the newest `runs/FY*`).
- Run everything from the project root (PowerShell). Scripts run with `python -I` unless their `--help` says otherwise (some run through `uvx`); `--help` itself always works with plain `python -I`.
- Python 3.13 with `pypdf`, `openpyxl` and `Pillow` (installed 3 Nov 2026, so `page.images` works on scanned PDFs); `curl.exe` for downloads.

## Scripts reference

| Script | Use it for | Caller step |
|---|---|---|
| [`run.py`](run.py) | Starting a run, listing its companies, checking what is pending | S1, S9, after S14 |
| [`screens.py`](screens.py) | Running the market screens and the whole-market sweep; building the universe | S2 |
| [`triage.py`](triage.py) | Scoring the universe and cutting gate batches | S3 |
| [`sectors.py`](sectors.py) | Any per-sector computation: sector numbers, order, call log, playbook episodes | S4, S5, S8R, S6 |
| [`gate_merge.py`](gate_merge.py) | Merging the gate decisions after the batches | S8R |
| [`scr_company.py`](scr_company.py) | Fetching one company's screener data (public mode) | S4, S8, S10, S13, S14 |
| [`scr_docs.py`](scr_docs.py) | Downloading a company's filings listed in its saved screener answers | S10 |
| [`scr_tool.py`](scr_tool.py) | Any single screener tool call saved to a file | S2 (through `screens.py`), ad hoc |
| [`facts_check.py`](facts_check.py) | Checking a company's `facts.json` against cached figures | S12 |
| [`pdf_text.py`](pdf_text.py) | Turning a PDF into text with page markers | S12, other scripts |
| [`thesis.py`](thesis.py) | Registering a company's thesis markers and checking them | S14, S11 |
| [`sheet_write.py`](sheet_write.py) | Writing the listing or allocation to the sheet with read-back | S14, S16 |
| [`kite_holdings.py`](kite_holdings.py) | Pulling holdings from Kite to the local copy and the sheet | S1, S15 |
| [`wf_lib.py`](wf_lib.py) | Shared helpers for the workflow scripts (not run) | imported |
| [`config.py`](config.py) | Every path the scripts use (not run) | imported |
| [`mb_universe.py`](mb_universe.py) | Building the playbook base data's market universe | S6 |
| [`mb_history.py`](mb_history.py) | Fetching long price and valuation history from the chart API | S4, S6 |
| [`mb_outcomes.py`](mb_outcomes.py) | Playbook base data: price and market-cap multiples per window | S6 |
| [`mb_features.py`](mb_features.py) | Playbook base data: point-in-time features | S6 |
| [`mb_patterns.py`](mb_patterns.py) | Playbook base data: staged pattern tests | S6 |
| [`mb_sector_test.py`](mb_sector_test.py) | Testing how concentrated winners are by industry (the sector premise test) | S6 |
| [`mb_sample.py`](mb_sample.py) | Playbook base data sample, when a playbook needs it | S6 (kept for playbooks) |
| [`mb_tag_batch.py`](mb_tag_batch.py) | Business-type tagging batches, when a playbook needs them | S6 (kept for playbooks) |
| [`ar_statements.py`](ar_statements.py) | Annual statements older than screener's, from annual reports | S6, S7 (`/workflow/ar_statements.md`) |
| [`ar_parsed_check.py`](ar_parsed_check.py) | Flagging doubtful parsed annual-report values | S6, S7 (`/workflow/ar_statements.md`) |
| [`ar_flag_reread.py`](ar_flag_reread.py) | Turning parsed-value flags into re-read rows for subagents | S6, S7 (`/workflow/ar_statements.md`) |
| [`ar_trim.py`](ar_trim.py) | Cutting annual-report text to the pages reading subagents need | S6, S7 (`/workflow/ar_statements.md`) |
| [`ar_fulltext.py`](ar_fulltext.py) | Whole-report text for reading subagents to search | S6, S7 (`/workflow/ar_statements.md`) |
| [`ar_helper_check.py`](ar_helper_check.py) | Checking reading subagents' values against the report | S6, S7 (`/workflow/ar_statements.md`) |
| [`ar_pdf_pages.py`](ar_pdf_pages.py) | Turning scanned annual-report pages into images | S6, S7 (`/workflow/ar_statements.md`) |
| [`bse_fetch.py`](bse_fetch.py) | BSE API items for companies NSE does not cover, through a browser | S12 (BSE-only companies) |
| [`bse_fetch.js`](bse_fetch.js) | The browser half of `bse_fetch.py` | S12 (BSE-only companies) |
| [`bse_shp.py`](bse_shp.py) | Fetching old shareholding patterns from BSE | S6 |
| [`bse_codes.py`](bse_codes.py) | Finding the BSE scrip code for an NSE symbol | manual, `bse_shp.py` |
| [`bse_pdf.py`](bse_pdf.py) | Fetching BSE announcement PDFs with a keyword search, when NSE has none | S12 (fallback) |
| [`save_b64_pdf.py`](save_b64_pdf.py) | Saving a PDF fetched in a browser as base64 | S12 (fallback) |
| [`save_js_file.py`](save_js_file.py) | Saving a large browser result to a file | S12 (fallback) |
| [`tt.py`](tt.py) | Tapetide API client, for manual use at the user's request | manual |
| [`tt_docs.py`](tt_docs.py) | Tapetide document fetching, for manual use at the user's request; its download functions also serve `scr_docs.py` | S10 (through `scr_docs.py`) |
