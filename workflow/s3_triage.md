# S3: number triage and gate batches (script, run by the orchestrator; full mode)

`python scripts/triage.py` reads `<run>/universe.csv` (screens and the whole-market sweep) and `<run>/holdings.csv` and writes:
- `<run>/triage.csv`: one row per company with the figures used, the return math per horizon, the earnings evidence and flags, and a `triage` decision with its reason;
- `<run>/gate_batches.json`: gate batches of 10 for every company queued, keeping earlier batch numbers (re-running adds only new names, plus any listed in `<run>/regate.txt`). S5's `sectors.py order` later reorders the batches not yet run, tailwind sectors first.

What the script decides: `/principles/filter_rules.md`. Holdings get `triage` = `holding` and go straight to S9.

The orchestrator records the printed counts in `progress.md`; a light-tier subagent spot-checks about ten rejects against screener's company pages (the figure each reject rests on, as printed there) and reports any that don't match.
