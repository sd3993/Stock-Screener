# P1: run setup and holdings (orchestrator)

1. **Run folder:** create `runs/<FYyyQn>/` (the latest ended quarter) with `progress.md` (claim line and checklist, per `process/README.md`) and an empty `status.csv` (header `sym,phase,state,stage,loops_to_p6,results_used,updated,note`). Set `RUN` in `tools/scripts/config.py`.
2. **Sheet:** create the tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1 (`tools/tools.md`, "The sheet").
3. **Holdings:** pull holdings from Zerodha Kite (`get_holdings`; if the session has expired, send the login link with the warning in `CLAUDE.md`) and save `<run>/holdings.csv` (sym, qty, avg_cost, fetched_at). If Kite fails, copy the last run's `holdings.csv` (or read the sheet's Holdings tab), tell the user, and carry on.
4. Holdings skip P3's rejects and P4's gate and always go on to P6, so they run through the full analysis with fresh figures.
