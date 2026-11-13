# S2: market screens and the whole-market sweep (script; full mode)

Runs every screen in `/workflow/screens.json` and the whole-market sweep on screener.in, saves every page, and builds the universe. No analysis, and never sector-only: the whole market is swept every full run (`/principles/sector_rules.md`). The orchestrator starts it from the project root:

`uvx --from screener-mcp==0.5.0 python scripts/screens.py run` (logged in, through the screener library; in the background, never beside another screener fetch; if screener.in can't be reached: `/sources/screener.md`). Its `--help` has the exact rules; in short:

- **screens** are the user's idea screens (T1…): every company that hits one joins the universe.
- **The sweep** covers the whole market (`base`: market cap above ₹250 cr, positive P/E) and gives S3 the figures it needs for every company, so names outside the screens can still qualify.
  - Each row carries the screener account's column set (`columns`; free accounts allow 15), so those fields come back for every company, empty or not, without being named in the query. A field named in a query drops the companies where it is empty.
  - The other fields S3 needs (`query_fields`) come from extra sweeps that name them in the query, so a company missing from one just has that field empty.
  - It runs in market-cap bands (`bands`, ₹ cr), each paged with full 200-row pages only.

1. **Column check first:** one row of `base` in a narrow market-cap range must hold every field in `columns`; if any is missing the script stops (exit 3) naming them: fix the account's column set (`/sources/screener.md`) or `screens.json`, then re-run.
2. **Query-field groups:** each remaining `query_fields` field is counted with `base` AND `<field> > -9999999`; fields with the same count are checked together, and share one extra sweep only when the combined count is unchanged. Counts and groups go to `<run>/screens/_groups.json` (delete it to redo the grouping).
3. **Every query** runs with `limit` 200, `min_market_cap` 0, `exclude_flagged` false and sorted by market cap: the screens (IDs `T<n>`), the bands (`B01`, `B02`, …, plus a last band above the highest bound) and the extra sweeps (`Q<group>B<band>`). A query of T rows takes desc pages 1 to floor(T/200), then one asc page 1 for the remainder (`/sources/screener.md`). A band under 200 rows is complete on its one page and is not merged with its neighbour.
4. **Each page goes straight to its file** `<run>/screens/<ID>_<desc|asc>_p<NN>.json`; saved pages are skipped, so a re-run resumes. A failed call waits 60 s and retries twice, then the script stops (exit 2) with the reason (login, rate limit): wait and re-run.
5. After each query the universe is rebuilt (`screens.py build`, also runnable alone with `python -I`) and checked: a query whose saved companies don't add up to its total stops the script (exit 3); a column that never came back counts only after the last query.

Done when the script ends with exit 0: every screen and band page saved, totals matching, and `<run>/universe.csv` built. Record its summary table (ID, total, pages, companies saved) and the universe size in `progress.md`.
