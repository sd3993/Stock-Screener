# P1: run setup and holdings (orchestrator)

1. **Run folder:** create `runs/future/<FYyyQn>/` (the latest ended quarter) with `progress.md` (claim line and checklist, per `process/future/README.md`) and an empty `status.csv` (header `sym,phase,state,stage,loops_to_p6,results_used,updated,note`). Set `RUN` in `tools/scripts/config.py`.
2. **Sheet:** create the tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1, through the `gws` CLI (`tools/tools.md`, "Google Sheets (`gws` CLI)") (layout: "The sheet").
3. **Holdings:** run `python tools/scripts/kite_holdings.py` (Kite CLI; saves `data/kite/holdings.csv`, the latest, and a dated JSON copy) and copy `data/kite/holdings.csv` to `<run>/holdings.csv`. If it exits 3 (not logged in), ask the user to run `kite auth login` with the warning in `CLAUDE.md`; if they aren't available (an unattended run), use the last saved `data/kite/holdings.csv` (or the sheet's Holdings tab if that's newer), tell the user its date, and carry on.
4. Holdings skip P3's rejects and P4's gate and always go on to P6, so they run through the full analysis with fresh figures.
