# S5: sector tailwind map (deep-tier subagent; full mode: build or review; recheck mode: marker review)

You build or review the sector map to the standards in `/principles/sector_rules.md`. Write only the files named below. Working directory: the project root (PowerShell). Your brief gives the run folder and the mode.

## Read first
`/principles/sector_rules.md`, `/principles/investing_rules.md` the news and events and sector preferences rules (what counts as news; the user's sector preferences), the run's `sector_clusters.csv` and `sector_stage.csv` (S4), the previous full run's `sector_map.md` and `sectors.json` if any, and the latest `python -I scripts/sectors.py score` output (past calls and how they fared; the orchestrator puts it in `<run>/sector_calls_score.md`).

## Build
Give an entry to every sector the sector standard names, with every item it requires, in `sector_map.md` in plain English and in `sectors.json`; every other queued company falls under "other".

## Review (a full run with a previous map, and recheck mode)
- For each existing entry, check every marker due by now: "script" ones from `<run>/marker_check.csv` (`thesis.py check --sectors`), "manual" ones against their named source. Record each state (held / broken / not yet due) with the date and evidence in `sectors.json`.
- A broken marker: rewrite the entry (or mark the tailwind ended), and put the sector and the reason at the top of your reply; the orchestrator tells the user, marks the sector's companies for re-analysis, and in recheck mode proposes a full run for that sector.
- Recheck mode: review only markers that are due or whose script state changed; add no new sector unless a major policy was notified (say so in your reply: it triggers a full run).
- Full-run review: also apply the entry criteria again and update stages from the new S4 numbers. State in `sector_map.md` how the last calls fared (from the score file).

## Output
- `<run>/sector_map.md`: one section per sector with the items above and their sources; then the order of work (sectors by rank with their queued companies and holdings), the playbook choices, the past calls' hit rate, and open questions.
- `<run>/sectors.json` (python, ensure_ascii=False): `{"as_of": date, "run": "<FYyyQn>", "sectors": [{"id", "name", "industries", "sub_sectors", "overrides": {sym: reason}, "kind", "evidence": [{"claim", "value", "date", "source", "url"}], "start", "end", "duration_why", "stage", "stage_reason", "capture", "capture_evidence", "headwinds": [..], "ends_if", "markers": [{"id", "text", "metric", "where", "op", "threshold", "event", "due", "by", "check", "state", "state_date", "state_evidence"}], "horizon", "rank", "playbook", "playbook_why", "call_date", "changed"}]}`.

Then the orchestrator runs `python -I scripts/sectors.py order` (writes `<run>/sector_of.tsv` and reorders the gate batches not yet run) and `python -I scripts/sectors.py log` (logs every new or changed call in `runs/sector_calls.csv`, and the marker states in `runs/sector_marker_states.csv`).

Reply with one line per sector: name, kind, stage, horizon, rank, playbook yes/no, markers changed; then anything you couldn't source.
