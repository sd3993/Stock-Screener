# S3: statements for the sample (script, run by the orchestrator)

For every company in `sample.csv`:
`uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM> --only statements,quarterly,shareholding,overview,documents,announcements,nse`
(no login, no model tokens; run them in a loop in the background, paced, and skip companies whose `scr/` is fresh from this study run).

This gives about 12 years of annual statements (consolidated and standalone), 13 quarters, 12 quarters of shareholding and pledge (`shp_history.json`), the annual-report list with exchange links back to about 2013, and NSE announcements.

Record in `status.md` the companies fetched and any failures with the reason. Older shareholding and filings for the stage studies (S5) are read from BSE/NSE documents there, not fetched here.
