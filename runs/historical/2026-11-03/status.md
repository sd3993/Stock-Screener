# Multibagger study: status of the current run

Method and steps: `process/historical/README.md`. This file records only where the run stands.

## Run 1 (task 2), started 3 Nov 2026
- **S6 done:** `experts.md` holds 34 findings, hypotheses H1-H20, and 4 corrections to the expert citations in rules 6, 8 and 9 (they go into `proposals.md` for the user's approval).
- **S1 done (3 Nov ~13:00):**
  - universe: 5,543 listed and 136 delisted candidates in `universe.csv` (every band matched screener's total); pages in `universe/`;
  - history: 5,678 of 5,679 fetched (2,867 new, 2,811 already cached); one failure, BSE code 538733, which screener doesn't match;
  - `outcomes.csv`: 5,570 companies, 259,796 company-quarter windows (the rest had no usable chart series).
- **S1 refetch (3 Nov ~13:15):** `mb_history.py` had kept consolidated chart series that were all empty (standalone-only companies such as Abbott India, Castrol, Bharat Dynamics), leaving no P/E or market cap. The first fix still asked for standalone wrongly (an empty `consolidated` parameter still returns consolidated; standalone needs it left out), so that refetch (13:08-16:35) gained nothing. Fixed again at 17:10, checked on Abbott India and a small BSE company (both now complete), and `--recheck-empty` is refetching the 2,102 affected companies (~3.5 hours). Then re-run `mb_outcomes.py`.
- **S2 next:** `tools/scripts/mb_sample.py` (seed 1) picks 200 winners, 100 fallen winners and 5 control candidates per winner into `sample_candidates.csv`; then overview/documents fetch, business types, controls, review.
- **3 Nov 2026:** the method moved from `plan.md` into `process/historical/`, adding the pattern tests (point in time, frequency and lift, mechanism, out of sample, whole-market precision) and business types from what companies actually do (user's direction).
- **3 Nov 2026:** layout changed (user's direction): the study's method is in `process/historical/`, this run's files in `runs/historical/2026-11-03/` (was `studies/multibaggers/`), and runs are committed. A partial `outcomes.csv` from an early test was deleted; S1 writes the full one.
