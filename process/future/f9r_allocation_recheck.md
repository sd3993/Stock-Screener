# F9R: allocation recheck checklist (Opus medium, with `process/future/recheck.md`)

Work file: `<run>/allocation/main.json` (recheck 1) or `recheck<N-1>.json`; your output: `recheck<N>.json`. Read `process/future/f9_allocation.md` first.

1. **Holdings:** quantities and average costs against `<run>/holdings.csv`, which the holdings script wrote from Kite just before F9 (no new Kite call; if that pull failed, Kite stale is TRUE and the file is the last saved copy).
2. **Inputs:** each company's CAGR, bear multiple, red reasons, evidence quality and bent rules against the bucket tabs and the Data tab.
3. **Rules:** sizing, bucket ranges and caps (rules 13, 15, 18), exits and the short-term target (rule 12), the tax date (rule 14); bucket shares add up and stay within ranges.
4. **Contrary evidence** for each Hold, Add and Buy: red reasons on the bucket tabs that the decision didn't weigh; for each Trim or Exit, evidence that the miss is temporary or marginal.
5. **Math:** target weights, target values, buy-below and sell-above prices.
