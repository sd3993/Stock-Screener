# P9: allocation and holdings (decide and rechecks: Opus medium; write: Sonnet low)

Three parts, each its own helper, in turn: **decide** (steps 1-4; write the decisions to `<run>/allocation/main.json`, with every value the two tabs need and the reasons), two **rechecks** (`process/future/recheck.md` with `process/future/p9r_allocation_recheck.md`; `recheck1.json`, `recheck2.json`), then **write** (P9W: steps 5-6, from the last recheck's file, copying values exactly). Never write into formula columns. Your brief gives the run folder and which part you do. The sheet is the Google Sheet "Stock Screener" (`1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU`), read and written through the `gws` CLI (`tools/tools.md`, "Google Sheets (`gws` CLI)").

1. Read `process/investing_rules.md` (buckets section and rules 12, 13, 14, 15, 18) and the run's `company_list.csv`.
2. **Holdings:** before P9 the orchestrator runs `python tools/scripts/kite_holdings.py`, which re-checks Kite for trades since P1 and writes the holdings' data columns to `data/kite/holdings.csv` and the Holdings tab (`tools/tools.md`, "Holdings script"); it copies `data/kite/holdings.csv` to `<run>/holdings.csv` and hands it over. If Kite fails (exit 3; the script has set Q Kite stale), it runs the script with `--latest <run>/holdings.csv` instead and tells you Kite is stale; carry on, don't stop. A stock now held that isn't on `company_list.csv` hasn't been analysed: list it in your reply, and the orchestrator runs it through P6-P8 before P9 runs again.
3. **Read the bucket tabs** (Short term, Medium term, Long term: live CAGR, bear multiple, "Below rule (live)" reasons) and the Data tab for each company's evidence quality, bent rules and non-negotiables.
4. **Decide**, per `process/investing_rules.md`:
   - sizing, bucket ranges and caps: rules 13, 15 and 18;
   - exits, including a multi-bucket stock hitting its short-term target: rule 12; the tax date: rule 14;
   - for each holding: Hold, Add, Trim or Full exit, weighing every red reason on the bucket tabs (a temporary or marginal miss may still be a hold; say why);
   - for new names: Buy (with target weight) or no position.
5. **Holdings tab** (sheetId 104): the script has already written each holding's data columns (Z, B, C, D, N, O, P, Q, V); never write them. Write only F Status (Hold/Add/Trim/Full exit) and M Notes (the reason in one line) on each holding's row (find it by ticker in Z), and remove the rows of sold holdings (Qty 0): clear their written columns B, C, D, F, M, N, O, P, Q, V, Z, never the formula columns, and never delete the row.
6. **Allocation tab** (sheetId 7), one row per position kept or bought: Z Ticker, B Name, C Action (Buy/Add/Hold/Trim/Exit), D Target weight, E Target value (₹), H Buy below (₹), I Sell above (₹), N Notes. Read back both tabs and compare with the file (Holdings: F and M; C and D against `<run>/holdings.csv`); fix any difference.

Reply with: holdings count, Kite fresh or stale, actions per holding (one line each), new buys with target weights, bucket shares vs ranges, and anything that breaches a cap.
