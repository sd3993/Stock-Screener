# Annual-report statements for years before screener's (`ar_statements.py`, and the reading subagent's brief)

Used only when a sector playbook (`/workflow/s6_playbook.md`) needs statements older than screener's ~12 years. Its state files (`ar_plan.csv`, `ar_status.csv`, `ar_links.csv`, `ar_missing.csv`) are in the playbook base data folder `data/playbook/` (`config.py`, `playbook_dir()`); the subagent queue and the parsed-value flags are rebuilt by `queue` and `ar_parsed_check.py` (the Nov 2026 copies are in `archive/past_2026-11-03/`).

## The scripts (run by the orchestrator; bseindia, so never beside another bseindia fetch)
- `python -I scripts/ar_statements.py plan` (needed years from `sample_candidates.csv`, default groups winner and fallen_winner; `--rows <csv> --groups <name>` for another list, e.g. a playbook's `episodes.csv`; `plan` overwrites `ar_plan.csv` and `fetch` and `queue` read only that file, so finish the list in hand, subagents included, before planning another), `fetch` (resumable; screener's annual-report links, then BSE link patterns; keeps the statement pages' text and a parsed JSON per report in `data/companies/<SYM>/FY<yy>Q4/`, deletes the PDF), then `queue`, which writes the two queues below. After a parser fix, `reparse` re-reads the saved pages without downloading. `ar_parsed_check.py` flags doubtful parsed values (`ar_parsed_flags.csv`); `ar_flag_reread.py` turns those flags into re-read rows for subagents.
- `ar_missing.csv` (no report found by link): a browser subagent collects their links from BSE's annual-report list into `ar_links.csv` (sym, fy, url) (`/sources/exchanges.md`); re-run `fetch`, which tries those first. A year BSE's list doesn't have stays in the file and its features stay blank.
- `ar_helper_queue.csv` (fields the parser couldn't read with confidence, in groups of about 25 reports): run `python -I scripts/ar_trim.py` (cuts the text each subagent reads) and `python -I scripts/ar_fulltext.py --tmp <empty scratch folder>` (whole-report text to search instead of reading PDFs) first, then reading subagents (light tier on trial, else standard; brief below), one group at a time. After each group, before the next: `python -I scripts/ar_helper_check.py <the group's rows>` lists values not printed in the report (noted arithmetic and scanned reports are expected; look into the rest); if the subagent's reply shows a parser fault, fix it and `reparse`; then run `queue`, which drops answered reports and renumbers the groups.
- **Only the fields that count:** these subagents are expensive (45 reports cost about 800k subagent tokens in Nov 2026). Brief them with only the fields the playbook's question uses, and send no report that lacks those fields.
- **Done when:** the subagent queue holds nothing still needed, and `ar_missing.csv` only years BSE's list doesn't have.

## Brief: reading annual-report statements the script couldn't (reading subagent)
You read the fields that `scripts/ar_statements.py` could not parse with confidence from old annual reports. Model work only where the script failed; nothing else.

**Input:** your rows of `ar_helper_queue.csv` (one group, about 25 reports): `sym`, `fy`, `fields` (`<basis initial>:<year end YYYY-MM>:<field|field…>`, `s` = standalone, `c` = consolidated), `page_text` (the statement pages, `=== page N ===` markers; `N` is the PDF page, `28L`/`28R` the left/right half of a two-up spread), `json` (the script's parse: per basis and year, `fields` = `[value in Rs crore, confidence, page]`, `checks`, `helper`), `url` (the report), `helper_file` (what you write).

**Read first:** the evidence standard for every value you write in `/principles/data_rules.md`, and the report units, layouts and field definitions in `/sources/ar_statements.md`.

### How to read
1. Open `ar_FY<yy>_stmt.txt` beside `page_text` if it exists (only the pages the statements should be on; `ar_trim.py`), and go to the full `page_text` only if it's missing or lacks a statement or schedule you need (schedules are often not in it: search the full file for them rather than reading it); find the basis's balance sheet, profit and loss account and cash flow statement (the `json` gives the pages the script used under `bases.<basis>.pages`, which may be wrong). Check the heading's date: it must be the year end in `fields`. Two columns: current year, then previous year.
2. `ar_FY<yy>_full.txt` beside `json`, if it exists, is the whole report's text (`ar_fulltext.py`): search it for a missing statement or schedule before going to the PDF. Only when it starts `SCANNED`, or is garbled, or `fields` says `scanned`: turn the PDF into images: `uvx --with pypdfium2 --with pillow python -I scripts/ar_pdf_pages.py --url "<url>" --dir <scratch folder>/<sym>_<fy> --sheets` writes contact sheets labelled with PDF page numbers; look at them to find the statement pages, run it again with `--pages 40-44,60` for those pages at reading size, read those PNGs, and delete the folder when done. Before leaving any asked basis or year blank, try all three: `_stmt.txt`, a search of `_full.txt`, then page images. Leave it blank only when the report truly doesn't print it, and note that. A subagent file marks the report as answered, so never write one with something unread that the report does print; if a report still can't be read after all three, write no file and say why in your reply.

### What to write back
One file per report, at `helper_file` (beside the script's `ar_FY<yy>.json`), UTF-8 JSON:
```json
{"sym": "SIMPLEXINF", "report": "FY10", "read_by": "helper", "read_on": "2026-11-05",
 "bases": {"standalone": {"2010-03": {"sales": 4443.48, "other_income": 22.62, "reserves": 959.73},
                          "2009-03": {"sales": 4652.11}}},
 "notes": {"standalone:2010-03:reserves": "Reserves and surplus 9,597,270 thousand (first of the two values; the second is shareholders' funds)"}}
```
- Write every field the queue lists for each basis and year (only those your brief names, if it narrows them), and nothing else unless a value the script parsed is wrong (then write the right value and say so in `notes`). A field you write overrides the script's; `null` means "not printed".
- Values in Rs crore (EPS in Rs), as numbers, not strings; keep the printed precision.
- If the script used the wrong pages or the wrong year for the whole report (or the report is scanned), read every field for every basis and year the report gives, add `"replace_parsed": true` and `"year_end": "YYYY-MM"` (its current year).
- If the report is not the company's or not an annual report, write `{"wrong_report": true, "notes": {...}}` and nothing else.

**Check before moving on:** right after writing each file, run `python -I scripts/ar_helper_check.py <your group's csv> --only <SYM> FY<yy>`. If it lists anything, go back for only that item: read what's missing, correct a wrong value, or add a note saying why a value or `null` is right (a sum, an image read, not printed). Then run it once more and go to the next report. When all are done, run it without `--only`, and clear or explain anything left in your reply.

`mb_features.py` and `ar_statements.py queue` pick the file up on their next run; nothing else to update. Reply with: reports done, fields written, fields left `null` and why, and anything the script got systematically wrong (with an example), so the parser can be fixed.
