# Scripts index

Single entry point for the deterministic scripts under `scripts/`: which script to use in which situation, and the step that calls it. Each script's `--help` (`python -I scripts/<name>.py --help`) holds its flags, command line, outputs, resume behaviour and checks before re-running.

## Running scripts

- Run from the project root (PowerShell) as `python -I scripts/<name>.py`, unless the script's `--help` says otherwise (some run through `uvx`); `--help` itself always works with plain `python -I`.
- The run folder comes from `config.py` (`RUN`, or the `RUN` environment variable, else the newest `runs/FY*`).
- Python 3.13 with `pypdf`, `openpyxl`, `Pillow` (so `page.images` works on scanned PDFs) and `pymupdf` (renders a page to an image, for tables drawn as graphics); `curl.exe` for downloads.

## Scripts reference

| Script | Use it for | Caller step |
|---|---|---|
| [`run.py`](run.py) | Starting a run, listing its companies, checking what is pending | S1, S7, after S12 |
| [`screens.py`](screens.py) | Running the market screens and the whole-market sweep; building the universe | S2 |
| [`triage.py`](triage.py) | Scoring the universe and cutting gate batches | S3 |
| [`sectors.py`](sectors.py) | Any per-sector computation: sector numbers, order and emerging queue, call log | S4, S5, S6R |
| [`gate_merge.py`](gate_merge.py) | Merging the gate decisions after the batches | S6R |
| [`scr_company.py`](scr_company.py) | Fetching one company's screener data (public mode) | S4, S6, S8, S11, S12 |
| [`scr_docs.py`](scr_docs.py) | Downloading a company's filings listed in its saved screener answers | S8 |
| [`scr_tool.py`](scr_tool.py) | Any single screener tool call saved to a file | S2 (through `screens.py`), ad hoc |
| [`facts_check.py`](facts_check.py) | Checking a company's `facts.json` against cached figures | S10 |
| [`pdf_text.py`](pdf_text.py) | Turning a PDF into text with page markers | S10, other scripts |
| [`thesis.py`](thesis.py) | Registering a company's thesis markers and checking them | S12, S9 |
| [`sheet_write.py`](sheet_write.py) | Writing the listing or allocation to the sheet with read-back | S12, S14 |
| [`sheet_layout.py`](sheet_layout.py) | Changing the sheet to the List + Watchlist layout, or repairing its headers, formulas and formats | manual (with the user's go-ahead) |
| [`kite_holdings.py`](kite_holdings.py) | Pulling holdings from Kite to the local copy and the sheet | S1, S13 |
| [`wf_lib.py`](wf_lib.py) | Shared helpers for the workflow scripts (not run) | imported |
| [`config.py`](config.py) | Every path the scripts use (not run) | imported |
| [`mb_history.py`](mb_history.py) | Fetching long price and valuation history from the chart API | S4 |
| [`bse_fetch.py`](bse_fetch.py) | BSE API items for companies NSE does not cover, through a browser | S10 (BSE-only companies) |
| [`bse_fetch.js`](bse_fetch.js) | The browser half of `bse_fetch.py` | S10 (BSE-only companies) |
| [`bse_pdf.py`](bse_pdf.py) | Fetching BSE announcement PDFs with a keyword search, when NSE has none | S10 (fallback) |
| [`save_b64_pdf.py`](save_b64_pdf.py) | Saving a PDF fetched in a browser as base64 | S10 (fallback) |
| [`save_js_file.py`](save_js_file.py) | Saving a large browser result to a file | S10 (fallback) |
