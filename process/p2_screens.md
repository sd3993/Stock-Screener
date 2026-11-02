# P2: market screens and field dumps (script; Sonnet low helper only when there's no API token)

Runs every screen and field dump in `process/screens.json` on Tapetide's fundamental screener and builds the universe. No analysis. Do not call any mcp__hearthbot__ tools. Working directory: the project root (PowerShell). The run folder (`runs/<FYyyQn>/`) is in your brief.

- **screens** are the user's idea screens (T1…): every company that hits one joins the universe.
- **dumps** cover the whole market (market cap above ₹250 cr, positive P/E; `dump_base`) and give P3 the figures it needs for every company, so names outside the screens can still qualify (the sweep). Each dump query is `dump_base` plus `AND <field> > -9999999` for each of its fields. Through MCP a query returns only two fields beyond the default columns, so each dump has two; the REST script first tries all fields in one query (`D_ALL`).

## With an API token (`TAPETIDE_TOKEN` set)
The orchestrator runs `python tools/scripts/tt_screens.py`, then `python tools/scripts/build_universe.py`. Both print totals; `tt_screens.py` resumes where it stopped if the quota runs out.

## Without a token (helper, Sonnet low)
1. Read the "Tapetide" section of `tools/tools.md`.
2. For each entry in `screens.json` (screens, then dumps), call `screen_stocks` with exactly its query, `limit` 25 (larger pages get cut off by the tool-result limit), sort and order as given (default: Market Capitalization, desc), page 1 to `total_pages`, one call at a time. Right after each call, save it with `python tools/scripts/save_last_result.py --marker total_pages --out <run>/screens/<ID>_p<NN>.json --page <page> --tag <tag>` (NN two digits; `<tag>` is the unique tag in your brief). Skip pages already saved.
3. If the quota runs out, stop and reply with where you stopped; never save a page twice or skip one.
4. Run `python tools/scripts/build_universe.py`.

Reply with: each screen's and dump's total and pages saved, the universe size, and anything that failed.
