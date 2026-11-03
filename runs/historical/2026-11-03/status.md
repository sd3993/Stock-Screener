# Multibagger study: status of the current run

Method and steps: `process/historical/README.md`. This file records only where the run stands.

## Run 1 (task 2), started 3 Nov 2026
- **S6 done:** `experts.md` holds 34 findings, hypotheses H1-H20, and 4 corrections to the expert citations in rules 6, 8 and 9 (they go into `proposals.md` for the user's approval).
- **S1 done (3 Nov ~13:00):**
  - universe: 5,543 listed and 136 delisted candidates in `universe.csv` (every band matched screener's total); pages in `universe/`;
  - history: 5,678 of 5,679 fetched (2,867 new, 2,811 already cached); one failure, BSE code 538733, which screener doesn't match;
  - `outcomes.csv`: 5,570 companies, 259,796 company-quarter windows (the rest had no usable chart series).
- **S2 under way:** sample selection per `process/historical/s2_sample.md`.
- **3 Nov 2026:** the method moved from `plan.md` into `process/historical/`, adding the pattern tests (point in time, frequency and lift, mechanism, out of sample, whole-market precision) and business types from what companies actually do (user's direction).
- **3 Nov 2026:** layout changed (user's direction): the study's method is in `process/historical/`, this run's files in `runs/historical/2026-11-03/` (was `studies/multibaggers/`), and runs are committed. A partial `outcomes.csv` from an early test was deleted; S1 writes the full one.
