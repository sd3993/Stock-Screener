# S13R: allocation recheck checklist (deep tier, run per `/workflow/recheck.md`)

Work file: `<run>/allocation/main.json` (recheck 1) or `recheck<N-1>.json`; your output: `recheck<N>.json`. Read `/workflow/s13_allocation.md` first.

1. **Holdings:** quantities and average costs against `<run>/holdings.csv`, which the holdings script wrote from Kite just before S13 (no new Kite call; if that pull failed, Kite stale is TRUE and the file is the last saved copy).
2. **Inputs:** each company's CAGR, bear multiple, buy-below price, red reasons, evidence quality and bent rules against the List, Watchlist and Data tabs; status, visible-until date, stage and marker states against `runs/companies/<SYM>/thesis.json` and `<run>/marker_check.csv`.
3. **Rules:** targets, starter sizes, trim lines and caps (the position size and count rule, the bent-rule tier and the allocation and rebalancing rule); exits and trims (the exit rules: none rests on a weak quarter, a price move or a high valuation alone, and every Full exit states its urgency); the cap shares add up, as the rules file currently words them.
4. **Contrary evidence** for each Hold, Add and Buy: red reasons on the List tab or broken markers that the decision didn't weigh; for each Trim or Exit, evidence that the thesis is intact (the miss temporary or marginal).
5. **Math:** target weights, target values, buy-below prices and trim lines.
