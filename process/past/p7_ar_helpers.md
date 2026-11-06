# P7.0 brief: reading annual-report statements the script couldn't (fallback helper)

You read the fields that `tools/scripts/ar_statements.py` could not parse with confidence from old annual reports, for the multibagger study's years before screener's statements (`p4_statements.md`, `p8_features.md`). Model work only where the script failed; nothing else.

**Input:** your rows of `runs/past/<date>/ar_helper_queue.csv` (one group, about 25 reports): `sym`, `fy`, `fields` (`<basis initial>:<year end YYYY-MM>:<field|field…>`, `s` = standalone, `c` = consolidated), `page_text` (the statement pages, `=== page N ===` markers; `N` is the PDF page, `28L`/`28R` the left/right half of a two-up spread), `json` (the script's parse: per basis and year, `fields` = `[value in Rs crore, confidence, page]`, `checks`, `helper`), `url` (the report), `helper_file` (what you write).

## Rule: figures only from the report
Every value you write is read from the report's own statement pages (or the schedule/note the statement points to), or is plain arithmetic on figures printed there (say which). Never estimate, never take a figure from memory, another source, a later report or screener. If a field is not printed and can't be computed from printed figures, write `null` and say why in `notes`.

## How to read
1. Open `ar_FY<yy>_stmt.txt` beside `page_text` if it exists (only the pages the statements should be on; `ar_trim.py`), and go to the full `page_text` only if it's missing or lacks a statement or schedule you need (schedules are often not in it: Grep the full file for them rather than reading it); find the basis's balance sheet, profit and loss account and cash flow statement (the `json` gives the pages the script used under `bases.<basis>.pages`, which may be wrong). Check the heading's date: it must be the year end in `fields`. Two columns: current year, then previous year.
2. Unit: read it from the page head ("Rs. in lakhs", "Rs. '000", "Rupees", "` in Crore"; "`" is the rupee sign in old fonts). Convert to **Rs crore**: lakh ÷ 100, thousand ÷ 10,000, million ÷ 10, rupees ÷ 10,000,000. EPS stays in rupees per share.
3. Old Schedule VI layout (to FY11): sources of funds (capital, reserves, loan funds, deferred tax) = application of funds (fixed assets, investments, current assets less current liabilities and provisions). Schedule III (FY12 on): equity and liabilities = assets.
4. `ar_FY<yy>_full.txt` beside `json`, if it exists, is the whole report's text (`ar_fulltext.py`): Grep it for a missing statement or schedule before going to the PDF. Only when it starts `SCANNED`, or is garbled, or `fields` says `scanned`: turn the PDF into images (the Read tool can't open PDFs here): `uvx --with pypdfium2 --with pillow python -I tools/scripts/ar_pdf_pages.py --url "<url>" --dir <scratchpad>/<sym>_<fy> --sheets` writes contact sheets labelled with PDF page numbers; Read them to find the statement pages, run it again with `--pages 40-44,60` for those pages at reading size, Read those PNGs, and delete the folder when done. Never write a helper file for a report you could not read (a file marks it as answered); say so in your reply.

## Fields (screener's definitions)
| field | what to write |
|---|---|
| `sales` | Revenue from operations net of excise duty (sales/income from operations less excise; several operating income lines are added up). Banks: interest earned. |
| `other_income` | Other income, including interest and dividend income shown separately, as printed. Exceptional items are added here by the script, so write other income without them and put them in `exceptional`. |
| `exceptional` | Exceptional / extraordinary items before tax (income +, expense −), if printed; else omit. |
| `interest` | Interest / finance costs (net, as printed). Banks: interest expended. |
| `dep` | Depreciation and amortisation charged to the P&L (net of any transfer from revaluation reserve). |
| `pbt` | Profit before tax (after exceptional items). |
| `tax` | Total tax expense (current + deferred + fringe benefit + earlier years − MAT credit); positive for a charge. |
| `pat` | Profit after tax, before minority interest and before share of associates if shown after it (consolidated). |
| `eps` | Basic EPS in rupees, as printed. |
| `dividend` | Equity dividend for the year (interim + proposed final), excluding dividend tax and preference dividend; 0 when the report shows none (say where you looked: appropriation section, reserves note, directors' report). |
| `equity_cap` | Equity share capital (paid-up). |
| `reserves` | Reserves and surplus (other equity), plus share warrants / share application money if shown in shareholders' funds. Negative P&L debit balance shown on the assets side is subtracted. |
| `borrowings` | All loans: secured + unsecured loans (old layout), or long-term + short-term borrowings (new layout; current maturities of long-term debt sit in other current liabilities: add them and say so). Banks: deposits + borrowings. 0 when no loan line exists. |
| `total_assets` | Balance-sheet total. Old layout: total of sources of funds + current liabilities and provisions (= fixed assets + investments + current assets, loans and advances + misc. expenditure not written off). New layout: the total as printed. |
| `debtors` | Sundry debtors / trade receivables (net). |
| `cfo` | Net cash from operating activities (cash flow statement, total "A"). |
| `year_end` | Only when the queue lists it: the year end the statements are for (`YYYY-MM`). |

## What to write back
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

`mb_features.py` and `ar_statements.py queue` pick the file up on their next run; nothing else to update. Reply with: reports done, fields written, fields left `null` and why, and anything the script got systematically wrong (with an example), so the parser can be fixed.
