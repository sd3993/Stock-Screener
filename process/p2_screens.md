# P2: market screens and the whole-market sweep (helper, Sonnet low)

Runs every screen in `process/screens.json` and the whole-market sweep on screener.in through its MCP, saves every page, and builds the universe. No analysis. Do not call any mcp__hearthbot__ tools. Working directory: the project root (PowerShell). The run folder (`runs/<FYyyQn>/`) and a unique tag are in your brief.

- **screens** are the user's idea screens (T1…): every company that hits one joins the universe.
- **The sweep** covers the whole market (`base`: market cap above ₹250 cr, positive P/E) and gives P3 the figures it needs for every company, so names outside the screens can still qualify.
  - Each row carries the screener account's column set (`columns`; free accounts allow 15), so those fields come back for every company, empty or not, without being named in the query. A field named in a query drops the companies where it is empty.
  - The other fields P3 needs (`query_fields`) come from extra sweeps that name them in the query, so a company missing from one just has that field empty.
  - It runs in market-cap bands (`bands`, ₹ cr), each paged with full 200-row pages only, so every answer goes to a file.

1. Read the "screener.in MCP" section of `tools/tools.md`.
2. **Check the column set first:** run `screen_stocks` with `base` AND a narrow market-cap range (`limit` 1) and check that the row holds every field in `columns`. If any is missing, stop and reply saying which. Note any `query_fields` that also came back on that row: those need no extra sweep.
   **Group the remaining `query_fields`:** count each with `base` AND `<field> > -9999999` (`limit` 1; the count is `total_matches`). Fields with the same count are checked together (`base` AND both fields): when that count is unchanged they cover the same companies and share one extra sweep. Otherwise each field gets its own. Record the counts and groups in `<run>/screens/_groups.json`.
3. **Every query** runs with `limit` 200, `min_market_cap` 0, `exclude_flagged` false and `sort_by` "Market Capitalization".
   - **Screens:** each screen's query exactly as written, ID `T<n>`.
   - **Bands:** `base` AND `Market Capitalization >= <lower> AND Market Capitalization < <upper>` for each pair of neighbouring `bands`, plus a last band above the highest bound, IDs `B01`, `B02`, ….
   - **Extra sweeps:** for each group, `base` AND `<field> > -9999999` for each field in it, run in the same bands, IDs `Q<group>B<band>` (e.g. `Q1B03`).
   - **Paging a query of T rows:** order desc, pages 1 to floor(T/200), then one order-asc page 1 for the remainder (overlap is fine; `tools/tools.md`). Merge a band under 200 rows with its neighbour and report the bounds used.
4. **Save each page right after its call:**
   - answer saved to a file by the app (it exceeded the tool-result limit): `python tools/scripts/scr_save.py --tool screen_stocks --args '<the call's arguments as JSON>' --out <run>/screens/<ID>_<desc|asc>_p<NN>.json --file <the path the app printed>`;
   - answer came inline: the same command with `--marker total_matches --tag <tag>` instead of `--file`.

   Never read a saved page into context. Skip pages already saved.
5. Run `python tools/scripts/build_universe.py`. It warns when a query's saved rows don't add up to its total, or when a column never came back: fix those and re-run.

Reply with: each screen's and band's total and pages saved, the universe size, any band you split, and anything that failed.
