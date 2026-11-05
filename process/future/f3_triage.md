# F3: number triage and gate batches (script, run by the orchestrator)

`python tools/scripts/triage.py` reads `<run>/universe.csv` (screens and the whole-market sweep) and `<run>/holdings.csv` and writes:
- `<run>/triage.csv`: one row per company with the figures used, the return math per bucket, the earnings evidence and flags, and a `triage` decision with its reason;
- `<run>/gate_batches.json`: gate batches of 10 for every company queued, keeping earlier batch numbers (re-running adds only new names, plus any listed in `<run>/regate.txt`).

What the script decides (from `process/investing_rules.md`):
- **Return math** per bucket (short 2 years, medium 5, long 7): the EPS growth needed for the 25% CAGR hurdle at exit P/E = min(own 5-year median P/E, 30), with dividends, against the growth visible in the trailing figures (conservative and optimistic).
- **Earnings evidence** (rule 6): E1 acceleration, E2 stalwart rebound, E3 sustained growth, E4 turnaround.
- **Queued for the gate:** a screen hit, or a non-screen name (the sweep) with earnings evidence, live return math and no hard flag.
- **Rejected here only when clearly failed**, by a margin a data error is unlikely to flip: return math dead in every bucket even at the optimistic growth plus 5 points; promoter pledge above 25% of promoter holding; cash conversion below 0.3 over both 2 and 5 years; REITs, InvITs and investment companies. Anything near a line goes to the gate instead.
- **Holdings** are never rejected or gated: `triage` = `holding`, and they go straight to F6.

The orchestrator reads the printed counts, checks that the rejects look right (spot-check a few against screener's company pages), and records the counts in `progress.md`.
