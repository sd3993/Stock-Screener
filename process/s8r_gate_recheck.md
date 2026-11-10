# S8R.n: gate recheck checklist (deep tier, with `process/recheck.md`)

Work file: `<run>/gate/bNN.json` (recheck 1) or `bNN_rc1.json`; your output: `bNN_rc<N>.json` as {"entries": [the corrected list, same format], plus the fields `process/recheck.md` adds}. Read `process/s8_gate.md` first, and each company's `<run>/gate/<SYM>.json`.

A wrong REJECT is never seen again, while every NEXT gets the full analysis and two rechecks in S13. So the weight of this recheck is on rejects:
- **Every REJECT** that isn't clearly dead on return math, **every borderline case** (best-horizon CAGR within ~5 points of the line) and **every floor call**: the full checklist below.
- **Clear REJECTs on return math:** check only that the math and its inputs are right.
- **Every NEXT:** check only the floors and integrity items (3 below), that nothing in the filings was missed (5), and the sector (6).

1. **Inputs:** P/E basis (one-offs normalised), growth used (guidance from the company's own exchange documents, under 12 months old, haircut by its record), exit P/E (rule 8 and the gate's adjustments), dividend yield: against the cached screener data, the gate file and the filing.
2. **Math:** redo the multiple and CAGR for the horizon used, and check whether another horizon would clear the line.
3. **Floors:** cash conversion, debt (lenders per rule 4's lender note), pledge, promoter selling or buying (rule 1.2's tests), integrity items, holding/investment companies, one-quarter spikes; each REJECT's `verified_against` points to the right page.
4. **Contrary evidence** for each REJECT checked: anything in the guidance documents, filings or figures that shows the growth or exit P/E was too low, or that the failed floor actually passes (a temporary cause, an improving trend, rule 2).
5. **Missed evidence:** a newer results filing, a guidance change, or a governance item the gate didn't read.
6. **Sector:** the confirmed sector follows from what the company does; no reject leans on the company being outside a tailwind sector.

**For the orchestrator:** after a batch's last recheck, run `python tools/scripts/gate_merge.py` (writes `<run>/gate/decisions.csv` from each batch's latest file). If a recheck finds an integrity flag, a deep-tier helper reads the filing before the reject stands. A company already gated this quarter isn't re-gated unless it filed something new or its price has fallen 20% or more since its gate check (add it to `<run>/regate.txt` and re-run `triage.py`). After the last batch, `python -I tools/scripts/sector_order.py --from-gate` applies the gate's sector corrections to `sector_of.tsv`.
