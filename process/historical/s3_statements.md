# S3: statements for the sample (script, run by the orchestrator)

Normally already done by S2's single fetch (`s2_sample.md`, "Order"); then S3 only checks that every `sample.csv` company has its files and fetches any that don't. For every company in `sample.csv`:
`uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM> --only statements,quarterly,shareholding,overview,documents,announcements,nse`
(no login, no model tokens; run them in a loop in the background, paced, and skip companies whose `scr/` is fresh from this study run).

This gives about 12 years of annual statements (consolidated and standalone), 13 quarters, 12 quarters of shareholding and pledge (`shp_history.json`), the annual-report list with exchange links back to about 2013, and NSE announcements.

Record in `status.md` the companies fetched and any failures with the reason. BSE-only companies have no NSE announcements or insider feed; the script saves an empty marker for them (`nse_listed: false`), so they aren't failures and `--skip-saved` doesn't ask again. No step needs them. Then the older shareholding the features need (the latest pattern filed by each start date and the 12 quarters before it, Mar 2001 - Jun 2022) comes from BSE: `python -I tools/scripts/bse_shp.py` (plain curl, resumable; `--plan` counts requests; usage in `tools/tools.md`, BSE). It needs each company's BSE code from `scr/overview.json`, so run it after the fetch above; it reports companies without one. Other older filings for the stage studies (S5) are read from BSE/NSE documents there, not fetched here.
