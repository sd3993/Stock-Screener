# S5: sector map (deep-tier subagent; full mode: build or review; recheck mode: marker review)

You build or review the sector map to the standards in `/principles/sector_rules.md`. Write only the files named below. Working directory: the project root (PowerShell). Your brief gives the run folder and the mode.

## Read first
`/principles/sector_rules.md`, `/principles/investing_rules.md` the news and events, sector preferences and use of history rules (what counts as news; the user's sector preferences; what the past may be used for), the run's `sector_clusters.csv` and `sector_stage.csv` (S4), the previous full run's `sector_map.md` and `sectors.json` if any, and the latest `python -I scripts/sectors.py score` output (past calls and how they fared; the orchestrator puts it in `<run>/sector_calls_score.md`).

## Emerging scan (full mode, before the clusters are read)
Search for emerging sectors and businesses first, so the search isn't steered by what the screens already caught:
1. **Problems:** from official sources only (the sector standard's forward-evidence sources, including the Economic Survey, regulators' consultation papers, draft policies and trade statistics on import dependence), list the bottlenecks that have to be solved, each with its figure, date and source.
2. **Companies:** for each problem, find the listed companies working on it (a web search or screener's search is only a pointer) and confirm each from its own exchange filings (pilot orders, approvals, capex, a new segment line).
3. **Not priced in:** apply the sector standard's emerging tests. Until the entry's stage numbers exist (`sector_stage.csv` with `--sectors`), judge the stage from the companies' own valuation, price strength and institutional-holding change.
4. Each one that passes becomes an entry marked emerging, its companies as overrides. List in your reply the problems you looked at and dropped, with the test each failed.

## Build
Give an entry to every sector the sector standard names, with every item it requires, in `sector_map.md` in plain English and in `sectors.json`; every other queued company falls under "other".

## Review (a full run with a previous map, and recheck mode)
- An entry that covers the same business keeps its id, whatever its name becomes: the call log and its score follow the id.
- For each existing entry, check every marker due by now: "script" ones from `<run>/marker_check.csv` (`thesis.py check --sectors`), "manual" ones against their named source. Record each state (held / broken / not yet due) with the date and evidence in `sectors.json`.
- A broken marker: rewrite the entry (or mark the tailwind ended), and put the sector and the reason at the top of your reply; the orchestrator tells the user, marks the sector's companies for re-analysis, and in recheck mode proposes a full run for that sector.
- Recheck mode: review only markers that are due or whose script state changed; add no new sector unless a major policy was notified (say so in your reply: it triggers a full run).
- Full-run review: also apply the entry criteria again (the emerging scan included; an emerging entry whose stage has reached recognised loses the mark) and update stages from the new S4 numbers. State in `sector_map.md` how the last calls fared (from the score file).

## Output
- `<run>/sector_map.md`: one section per sector with the items above and their sources; then the order of work (sectors by rank with their queued companies and holdings), the emerging entries with the problems looked at and dropped, the past calls' hit rate, and open questions.
- `<run>/sectors.json` (python, ensure_ascii=False): `{"as_of": date, "run": "<FYyyQn>", "sectors": [{"id", "name", "industries", "sub_sectors", "overrides": {sym: reason}, "kind", "emerging" (true/false), "problem" (emerging only: {"text", "value", "date", "source", "url"}), "evidence": [{"claim", "value", "date", "source", "url"}], "start", "end", "duration_why", "stage", "stage_reason", "capture", "capture_evidence", "headwinds": [..], "ends_if", "markers": [{"id", "text", "metric", "where", "op", "threshold", "event", "due", "by", "check", "state", "state_date", "state_evidence"}], "rank", "call_date", "changed"}]}`.

Then the orchestrator runs `python -I scripts/sectors.py order` (writes `<run>/sector_of.tsv`, reorders the gate batches not yet run and queues the emerging entries' companies) and `python -I scripts/sectors.py log` (logs every new or changed call in `runs/sector_calls.csv`, and the marker states in `runs/sector_marker_states.csv`).

Reply with one line per sector: name, kind, emerging or not, stage, rank, markers changed; then the problems dropped in the emerging scan, and anything you couldn't source.
