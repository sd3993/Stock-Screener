# S15R: allocation recheck checklist (deep tier, with `process/recheck.md`)

Work file: `<run>/allocation/main.json` (recheck 1) or `recheck<N-1>.json`; your output: `recheck<N>.json`. Read `process/s15_allocation.md` first.

1. **Holdings:** quantities and average costs against `<run>/holdings.csv`, which the holdings script wrote from Kite just before S15 (no new Kite call; if that pull failed, Kite stale is TRUE and the file is the last saved copy).
2. **Inputs:** each company's CAGR, bear multiple, red reasons, evidence quality and bent rules against the horizon tabs and the Data tab; horizon, stage and marker states against `runs/theses/` and `<run>/marker_check.csv`.
3. **Rules:** sizing, ranges and caps (rules 13, 15, 18), exits and marker breaks by horizon (rule 12), the tax date (rule 14); shares add up and stay within ranges, as the rules file currently words them.
4. **Contrary evidence** for each Hold, Add and Buy: red reasons on the horizon tabs or broken markers that the decision didn't weigh; for each Trim or Exit, evidence that the miss is temporary or marginal.
5. **Math:** target weights, target values, buy-below and sell-above prices.
