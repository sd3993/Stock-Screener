# S5: stage studies (one Opus high helper per company, then one Opus medium recheck)

About 30 winners (10 per horizon) and about 10 fallen winners, picked in `backtest.md` across business types and periods. One company at a time; each study's learnings go into the next helper's brief.

**Helper brief:** the company, its winning window, its business type from `business_types.csv`, and `backtest.md`'s patterns to test. Working directory: the project root.

1. **No hindsight:** for each stage, read only documents dated before it (annual reports from the screener list back to about 2013, results, transcripts and presentations from BSE/NSE; `process/data_rules.md`, `tools/tools.md`). Older years only from what was filed then.
2. **The actual business:** what the company does, how it earns, what drives revenue and margins (volumes, prices, order book, capacity, mix, regulation), and how that changed across the window. Confirm or correct its business type, saying why.
3. **Stages:** overlooked, earnings turn, re-rating, compounding, de-rating; for each, the dates, the trigger, how long it lasted, and the price, P/E and EPS change.
4. **What was visible at the time:** for each stage start, which signals an investor could have seen in the filings and figures then, and which of `backtest.md`'s patterns were present; for a fallen winner, the signs before the fall.
5. Write `runs/historical/<date>/stages/<SYM>.md` and reply with a 5-line summary: business type, stages with dates, the early signals, patterns confirmed or contradicted, and anything learned for the next study.

**Recheck** (`process/future/recheck.md`): one Opus medium helper checks dates, figures and the no-hindsight rule against the cited documents, and that the business-type reading follows from them; corrections are made in the file.
