# P9: allocation and holdings (decide and rechecks: Opus medium; write: Sonnet low)

Three parts, each its own helper, in turn: **decide** (steps 1-4; write the decisions to `<run>/allocation/main.json`, with every value the two tabs need and the reasons), two **rechecks** (`process/recheck.md` with `process/p9r_allocation_recheck.md`; `recheck1.json`, `recheck2.json`), then **write** (P9W: steps 5-6, from the last recheck's file, copying values exactly). Never write into formula columns. Do not call any mcp__hearthbot__ tools. Your brief gives the run folder and which part you do. The sheet is the Google Sheet "Stock Screener" (`1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU`).

1. Read `process/investing_rules.md` (buckets section and rules 12, 13, 14, 15, 18) and the run's `company_list.csv`.
2. **Holdings:** start from `<run>/holdings.csv` (pulled from Kite in P1) and re-check Zerodha Kite (`get_holdings`) for trades made since. Update quantities and average costs. A stock now held that isn't on `company_list.csv` hasn't been analysed: list it in your reply, and the orchestrator runs it through P6-P8 before P9 runs again. If Kite fails or needs a login, carry on with `holdings.csv`, set column Q (Kite stale) to TRUE on every holdings row, and say so in your reply; don't stop.
3. **Read the bucket tabs** (Short term, Medium term, Long term: live CAGR, bear multiple, "Below rule (live)" reasons) and the Data tab for each company's evidence quality, bent rules and non-negotiables.
4. **Decide**, per `process/investing_rules.md`:
   - sizing, bucket ranges and caps: rules 13, 15 and 18;
   - exits, including a multi-bucket stock hitting its short-term target: rule 12; the tax date: rule 14;
   - for each holding: Hold, Add, Trim or Full exit, weighing every red reason on the bucket tabs (a temporary or marginal miss may still be a hold; say why);
   - for new names: Buy (with target weight) or no position.
5. **Holdings:** update `<run>/holdings.csv` if Kite showed changes, then write the **Holdings tab** (sheetId 104), one row per holding: Z Ticker, B Name, C Qty, D Avg cost, F Status (Hold/Add/Trim/Full exit), M Notes (the reason in one line), N Google code, O Screener URL, P Stored price, Q Kite stale (TRUE/FALSE).
6. **Allocation tab** (sheetId 7), one row per position kept or bought: Z Ticker, B Name, C Action (Buy/Add/Hold/Trim/Exit), D Target weight, E Target value (₹), H Buy below (₹), I Sell above (₹), N Notes. Read back both tabs and compare with the file; fix any difference.

Reply with: holdings count, Kite fresh or stale, actions per holding (one line each), new buys with target weights, bucket shares vs ranges, and anything that breaches a cap.
