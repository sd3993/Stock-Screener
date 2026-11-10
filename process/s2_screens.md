# S2: market screens and the whole-market sweep (helper, light tier on trial, else standard; full mode)

Runs every screen in `process/screens.json` and the whole-market sweep on screener.in through `scr_tool.py` (logged in), saves every page, and builds the universe. No analysis, and never sector-only: the whole market is swept every full run (`process/README.md`, "Two modes"). Working directory: the project root; run `scr_tool.py` from a bash shell (`tools/tools.md`). The run folder (`runs/<FYyyQn>/`) is in your brief. (`run_screens.py`, to write, will do all of this by script; `runs/new_scripts_spec.md`.)

- **screens** are the user's idea screens (T1…): every company that hits one joins the universe.
- **The sweep** covers the whole market (`base`: market cap above ₹250 cr, positive P/E) and gives S3 the figures it needs for every company, so names outside the screens can still qualify.
  - Each row carries the screener account's column set (`columns`; free accounts allow 15), so those fields come back for every company, empty or not, without being named in the query. A field named in a query drops the companies where it is empty.
  - The other fields S3 needs (`query_fields`) come from extra sweeps that name them in the query, so a company missing from one just has that field empty.
  - It runs in market-cap bands (`bands`, ₹ cr), each paged with full 200-row pages only.

1. Read the "screener.in" section of `tools/tools.md`. Every call below is `uvx --from screener-mcp==0.5.0 python tools/scripts/scr_tool.py screen_stocks '<args as JSON>' <out> --login`.
2. **Check the column set first:** run it with `base` AND a narrow market-cap range (`limit` 1, out `<run>/screens/_probe/columns.json`) and check that the file's one row holds every field in `columns`. If any is missing, stop and reply saying which. Note any `query_fields` that also came back on that row: those need no extra sweep.
   **Group the remaining `query_fields`:** count each with `base` AND `<field> > -9999999` (`limit` 1, out `<run>/screens/_probe/<field>.json`; the count is the total the script prints). Fields with the same count are checked together (`base` AND both fields): when that count is unchanged they cover the same companies and share one extra sweep. Otherwise each field gets its own. Record the counts and groups in `<run>/screens/_groups.json`.
3. **Every query** runs with `limit` 200, `min_market_cap` 0, `exclude_flagged` false and `sort_by` "Market Capitalization".
   - **Screens:** each screen's query exactly as written, ID `T<n>`.
   - **Bands:** `base` AND `Market Capitalization >= <lower> AND Market Capitalization < <upper>` for each pair of neighbouring `bands`, plus a last band above the highest bound, IDs `B01`, `B02`, ….
   - **Extra sweeps:** for each group, `base` AND `<field> > -9999999` for each field in it, run in the same bands, IDs `Q<group>B<band>` (e.g. `Q1B03`).
   - **Paging a query of T rows:** order desc, pages 1 to floor(T/200), then one order-asc page 1 for the remainder (overlap is fine; `tools/tools.md`). Merge a band under 200 rows with its neighbour and report the bounds used.
4. **Each page goes straight to its file:** out `<run>/screens/<ID>_<desc|asc>_p<NN>.json`. Never read a saved page into context. Skip pages already saved. A call that exits non-zero: check the reason in its file (login, rate limit), wait and re-run it.
5. Run `python tools/scripts/build_universe.py` after each query's pages, before the next query. It warns when a query's saved rows don't add up to its total, or when a column never came back: fix those and re-run. The last run gives the full universe.

Reply with: each screen's and band's total and pages saved, the universe size, any band you split, and anything that failed.

**Light-tier trial:** on the first run at the light tier, the output is accepted only if `build_universe.py`'s last run prints no warning and every band total matches screener's; otherwise the missing queries are redone at the standard tier and the orchestrator records the switch in `process/README.md`.
