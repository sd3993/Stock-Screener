# P4.0, P5.0, P6.0: statements for the sample and the lists P8 writes (scripts, run by the orchestrator); P7.0: the helpers on what they leave

## P4.0: statements

Normally already done by P2's single fetch (`p2_sample.md`, "Order"); then P4 only checks that every `sample.csv` company has its files and fetches any that don't. For every company in `sample.csv`:
`uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM> --only statements,quarterly,shareholding,overview,documents,announcements,nse`
(no login, no model tokens; run them in a loop in the background, paced, and skip companies whose `scr/` is fresh from this study run).

This gives about 12 years of annual statements (consolidated and standalone), 13 quarters, 12 quarters of shareholding and pledge (`shp_history.json`), the annual-report list with exchange links back to about 2013, and NSE announcements.

**Market statements:** when a pattern using statements reaches P8's out-of-sample stage, P8 writes `market_fetch.txt` (companies with a start market cap of ₹50 cr or more in 2016-2023 and no saved statements); fetch it with `--only statements,overview --skip-saved` in the background. Check `data/` against the storage budget (`CLAUDE.md`, "Storage") first.

Record in `status.md` the companies fetched and any failures with the reason. BSE-only companies have no NSE announcements or insider feed; the script saves an empty marker for them (`nse_listed: false`), so they aren't failures and `--skip-saved` doesn't ask again. No step needs them.

## P5.0: BSE shareholding
The older shareholding the features need (the latest pattern filed by each start date and the 12 quarters before it, Mar 2001 - Jun 2022) comes from BSE: `python -I tools/scripts/bse_shp.py` (plain curl, resumable; `--plan` counts requests; usage in `tools/tools.md`, BSE). It needs each company's BSE code from `scr/overview.json`, so run it after the fetch above; it reports companies without one. Beyond `sample.csv`, fetch only `peer_panel.csv` (`--rows`), and only once a shareholding pattern needs it.

## P6.0: annual-report statements
Statements for the years before screener's (P8's features look back up to 6 years from each window start) come from the annual reports: `python -I tools/scripts/ar_statements.py plan` (needed years from `sample_candidates.csv`; default groups winner and fallen_winner; `--rows peer_panel.csv --groups peer` for P8's peers, and for the frozen controls only once a pattern reaches their cross-check; `plan` overwrites `ar_plan.csv`, so name every group still needed), `fetch` (resumable; screener's annual-report links, then BSE link patterns; keeps the statement pages' text and a parsed JSON per report, deletes the PDF), then `queue`, which writes the two queues P7 works on. After a parser fix, `reparse` re-reads the saved pages without downloading. Other older filings for the stage studies (P10) are read from BSE/NSE documents there, not fetched here.

## P7.0: annual-report helpers (Sonnet low; then back to P6 until both queues are empty)
- `ar_missing.csv` (no report found by link): a browser helper (`CLAUDE.md`, "Browser fetches") collects their links from BSE's annual-report list into `ar_links.csv` (sym, fy, url) in the run folder; the orchestrator re-runs `fetch`, which tries those first.
- `ar_helper_queue.csv` (fields the parser couldn't read with confidence, in groups of about 25 reports): fallback helpers, briefed by `p7_ar_helpers.md`.
