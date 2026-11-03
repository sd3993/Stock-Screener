# P7: in-depth analysis (Opus high, one company per helper)

You analyse one company in depth and write one analysis file (`main`); two rechecks then correct it (`process/future/recheck.md`). Never read an earlier quarter's analysis of this company unless your brief says this is a re-research, and then only after your own analysis is finished, to write the "what changed" note. Do not edit `process/investing_rules.md`, the sheet or any file outside your output. Working directory: the project root (PowerShell). Your brief gives the company, the run folder (`runs/future/<FYyyQn>/`), whether the company is a holding, and whether this is a re-research.

## Read first
- `process/investing_rules.md` in full, including the sector notes for this company's sector.
- `process/data_rules.md` and the top two sections and the "screener.in MCP" section of `tools/tools.md`.
- The company's sector entry in `<run>/sector_map.md`, and its gate file `<run>/gate/<SYM>.json` if it has one (its `for_p7` items must be answered).
- `data/companies/<SYM>/`: `index.json`, `facts.json`, `facts_check.json` and the documents (never the `_superseded` ones); the cached answers in `scr/` (and `bse/`, `api/` where present).

## Before analysing: newer results?
Refresh the company's announcements (`uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM> --only announcements`; no model tokens). If the company has declared results newer than `latest_declared_quarter` in `index.json`, stop and reply only `NEW_RESULTS: <FYyyQn>` (unless your brief says the loop cap is reached; then note it and carry on).

## The analysis
Apply `process/investing_rules.md` throughout, weighing what the company passes against what it fails. Your results must not depend on today's share price: give EPS paths, exit P/Es and judgements only; the sheet computes P/E, PEG, multiples and CAGR from live prices.
1. **Figures:** resolve every `facts_check.json` mismatch against the filing (rule out definition gaps first); list each genuine source-vs-filing mismatch (screener or Tapetide) as a data flag. Fetch anything missing yourself (per `process/data_rules.md`), say what you fetched, and add a line to `process/fetch_learnings.md` (re-read it just before writing; no duplicates) so P6 fetches it next time.
2. **Normalised trailing EPS:** strip one-offs (rule 6).
3. **Non-negotiables** (rule 1): Pass / Bent / Fail for each of the four, with the evidence and its source; name any that fail.
4. **Every negative** (rule 2): the cause with its source, temporary or structural, management's record on it, whether it is improving now. Keep a guidance-vs-delivery scorecard for the last 4-8 quarters.
5. **Bucket eligibility** per rule 7 and the buckets section (nested). If the company is a holding eligible for none, name the closest bucket.
6. **EPS paths:** base EPS at year 1; base and bear EPS at year 2, and at years 5 and 7 where medium/long are eligible (or the closest bucket for a holding). Build them from guidance (haircut by the scorecard), order book, capacity coming online and margins; say how.
7. **Exit P/E for each eligible bucket**, set exactly as rule 8 says, including both sanity checks. The own 5-year median P/E: the "Historical PE 5Years" figure in `<run>/universe.csv`, or computed from year-end P/Es in screener's ratios table (`scr/ratios.json`) (say which). Name the hand-picked peers with their 5-year median P/Es, found the same way.
8. **Evidence quality** (High / Medium / Low): filed orders and running capacity rank above guidance, guidance above extrapolation.
9. **Bent rules** (rule 15), **thesis**, **kill condition** and **review date**.
10. **Sector notes:** if this company shows a sector note in `process/investing_rules.md` is wrong or missing, propose the change (old and new wording, reason, evidence). Don't edit the rules file.

## Output
Write `<run>/analysis/<SYM>/main.json` (python, ensure_ascii=False) with:
sym, name, sector, analysed_on, results_used (FYyyQn), held (true/false), eps_ttm_normalised, eps_y1_base, short {eligible, eps_y2_base, eps_y2_bear, exit_pe, exit_pe_reasoning}, medium {eligible, eps_y5_base, eps_y5_bear, exit_pe, exit_pe_reasoning}, long {eligible, eps_y7_base, eps_y7_bear, exit_pe, exit_pe_reasoning}, closest_bucket (holdings eligible for none, else null), dividend_per_share_per_year, peers [{name, pe_5y_median, source}], evidence_quality, non_negotiables {pledge, promoter_selling, governance, cash_conversion: {status, evidence, source}}, nonneg_overall (Pass/Bent/Fail), nonneg_failed [names], negatives [{metric, numbers, cause, source, temporary_or_structural, management_record, improving}], guidance_scorecard [..], bent_rules [..], thesis, kill_condition, review_date, data_flags [{item, what_disagreed, values_seen, value_used_and_why}], sector_note_proposals [..], fetched_extra [..], unknowns [..], sources [..].
Also write `<run>/analysis/<SYM>/main.md`: a plain-English summary for the user (verdict per bucket, the deciding evidence, the main risks). On a re-research, open it with what changed from the previous analysis and why.

Reply with: buckets eligible, non-negotiables overall, base EPS at years 2/5/7, exit P/Es, evidence quality, and any sector-note proposal, one line each.
