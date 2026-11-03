# Multibagger study: status of the current run

Method and steps: `process/study_multibaggers/README.md`. This file records only where the run stands.

## Run 1 (task 2), started 3 Nov 2026
- **S6 done:** `experts.md` holds 34 findings, hypotheses H1-H20, and 4 corrections to the expert citations in rules 6, 8 and 9 (they go into `proposals.md` for the user's approval).
- **S1 under way:**
  - universe: 5,543 listed and 136 delisted candidates in `universe.csv` (every band matched screener's total); pages in `universe/`;
  - history: `mb_history.py --csv studies/multibaggers/universe.csv` running in the background since 3 Nov ~09:51 (log `mb_history.log` in the session scratchpad; half-hourly watchdog); 4,178 of 5,679 saved at ~11:30, no failures;
  - next: `python -I tools/scripts/mb_outcomes.py` when it ends, then S2.
- **3 Nov 2026:** the method moved from `plan.md` into `process/study_multibaggers/`, adding the pattern tests (point in time, frequency and lift, mechanism, out of sample, whole-market precision) and business types from what companies actually do (user's direction).
