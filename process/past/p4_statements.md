# P4.0, P5.0, P6.0: statements for the sample and the lists P8 writes (scripts, run by the orchestrator); P7.0: the helpers on what they leave

P4 uses screener, P5 and P6 bseindia: P4 can run beside either, while P5 and P6 run one after the other.

## P4.0: statements

Normally already done by P2's single fetch (`p2_sample.md`, "Order"); then P4 only checks that every `sample.csv` company has its files and fetches any that don't. For every company in `sample.csv`:
`uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM> --only statements,quarterly,shareholding,overview,documents,announcements,nse`
(no login, no model tokens; run them in a loop in the background, paced, and skip companies whose `scr/` is fresh from this study run).

This gives about 12 years of annual statements (consolidated and standalone), 13 quarters, 12 quarters of shareholding and pledge (`shp_history.json`), the annual-report list with exchange links back to about 2013, and NSE announcements.

**Market statements (needed for P8.3; no tokens, so fetched early, alongside the other scripts, while patterns using statements are alive):** `mb_patterns.py market_fetch --force` writes `market_fetch.txt` (companies with a start market cap of ₹50 cr or more in 2016-2023 and no saved statements); fetch it with `--only statements,overview --skip-saved` in the background.

Record in `status.md` the companies fetched and any failures with the reason. BSE-only companies have no NSE announcements or insider feed; the script saves an empty marker for them (`nse_listed: false`), so they aren't failures and `--skip-saved` doesn't ask again. No step needs them.

## P5.0: BSE shareholding
The older shareholding the features need (the latest pattern filed by each start date and the 12 quarters before it, Mar 2001 - Jun 2022) comes from BSE: `python -I tools/scripts/bse_shp.py --rows runs/past/<date>/sample.csv` (plain curl, resumable; `--plan` counts requests, 0 when done; usage in `tools/tools.md`, BSE). It needs each company's BSE code from `scr/overview.json` (else `data/market/bse_codes.csv`), so run it after the fetch above; it reports companies without one. Beyond `sample.csv`, fetch only `peer_panel.csv` (`--rows`), and only once a shareholding pattern needs it.

## P6.0: annual-report statements
Statements for the years before screener's (P8's features look back up to 6 years from each window start) come from the annual reports: `python -I tools/scripts/ar_statements.py plan` (needed years from `sample_candidates.csv`; default groups winner and fallen_winner; `--rows peer_panel.csv --groups peer` for P8's peers, and for the frozen controls only once a pattern reaches their cross-check; `plan` overwrites `ar_plan.csv` and `fetch` and `queue` read only that file, so finish the list in hand, P7 included, before planning another), `fetch` (resumable; screener's annual-report links, then BSE link patterns; keeps the statement pages' text and a parsed JSON per report, deletes the PDF), then `queue`, which writes the two queues P7 works on. After a parser fix, `reparse` re-reads the saved pages without downloading. Other older filings for the stage studies (P10) are read from BSE/NSE documents there, not fetched here.

## P7.0: annual-report helpers (Sonnet low; then back to P6 until the queues are done)
- `ar_missing.csv` (no report found by link): a browser helper (`CLAUDE.md`, "Browser fetches") collects their links from BSE's annual-report list into `ar_links.csv` (sym, fy, url) in the run folder; the orchestrator re-runs `fetch`, which tries those first. A year BSE's list doesn't have stays in the file: record it in `status.md`; its features stay blank (`features_coverage.md`).
- `ar_helper_queue.csv` (fields the parser couldn't read with confidence, in groups of about 25 reports): run `python -I tools/scripts/ar_trim.py` first (cuts the text each helper reads), then fallback helpers, briefed by `p7_ar_helpers.md`, one group at a time. After each group, before the next: `python -I tools/scripts/ar_helper_check.py <the group's rows>` lists values not printed in the report (noted arithmetic and scanned reports are expected; look into the rest); if the helper's reply shows a parser fault, fix it and `reparse`; then run `queue`, which drops answered reports and renumbers the groups, so the next helper takes group 1.
- **Peer panel, only the fields that count:** these helpers are expensive (the last 45 reports cost about 800k helper tokens). For `peer_panel.csv`, brief them with only the fields that patterns surviving the earlier stages use, and send no report that lacks those fields; the other fields stay blank in the features.
- **Done when:** the helper queue holds nothing still needed, and `ar_missing.csv` only years BSE's list doesn't have.
