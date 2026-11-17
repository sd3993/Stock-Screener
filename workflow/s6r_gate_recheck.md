# S8R.n: gate recheck checklist (deep tier, run per `/workflow/recheck.md`)

Work file: `<run>/gate/bNN.json` (recheck 1) or `bNN_rc1.json`; your output: `bNN_rc<N>.json` as {"entries": [the corrected list, same format], plus the fields `/workflow/recheck.md` adds}. Read `/workflow/s8_gate.md` and `/principles/filter_rules.md` first, and each company's `<run>/gate/<SYM>.json`.

A wrong REJECT is never seen again, while every NEXT gets the full analysis and two rechecks in S13. So the weight of this recheck is on rejects:
- **Every REJECT** that isn't clearly dead on return math, **every borderline case** (best-horizon CAGR within ~5 points of the line) and **every floor call**: the full checklist below.
- **Clear REJECTs on return math:** check only that the math and its inputs are right.
- **Every NEXT:** check only the floors and integrity items (3 below), that nothing in the filings was missed (5), and the sector (6).

1. **Inputs:** P/E basis (one-offs normalised), growth used, exit P/E and dividend yield, each as the gate standard sets it: against the cached screener data, the gate file and the filing.
2. **Math:** redo the multiple and CAGR for the horizon used, and check whether another horizon would clear the line.
3. **Floors:** each floor of the gate standard, and promoter buying against the promoter selling and buying rule's tests; each REJECT's `verified_against` points to the right page.
4. **Contrary evidence** for each REJECT checked: anything in the guidance documents, filings or figures that shows the growth or exit P/E was too low, or that the failed floor actually passes (a temporary cause, an improving trend, the trajectory rule).
5. **Missed evidence:** a newer results filing, a guidance change, or a governance item the gate didn't read.
6. **Sector:** the confirmed sector follows from what the company does; no reject leans on the company being outside a tailwind sector.

**For the orchestrator:** after a batch's last recheck, run `python scripts/gate_merge.py` (writes `<run>/gate/decisions.csv` from each batch's latest file). If a recheck finds an integrity flag, a deep-tier subagent reads the filing before the reject stands. To re-gate a company the gate standard lets back in, add it to `<run>/regate.txt` and re-run `triage.py`. After the last batch, `python -I scripts/sectors.py order --from-gate` applies the gate's sector corrections to `sector_of.tsv`.
