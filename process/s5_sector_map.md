# S5: sector tailwind map (deep-tier helper; full mode: build or review; recheck mode: marker review)

The map frames the work: it orders companies through the gate and the analysis (tailwind sectors first), sets the horizon and re-rating case each company's thesis starts from, and chooses which sectors get a playbook (S6-S7). It never removes a company: screening stays market-wide, and a company in a sector with no tailwind is still gated and analysed, only later in the order (`process/README.md`, "Two modes"). Write only the files named below. Working directory: the project root (PowerShell). Your brief gives the run folder and the mode.

## Read first
`process/investing_rules.md` rules 16 and 21 (what counts as news; the user's sector preferences), the run's `sector_clusters.csv` and `sector_stage.csv` (S4), the previous full run's `sector_map.md` and `sectors.json` if any, and the latest `python -I tools/scripts/sector_calls.py score` output (past calls and how they fared; the orchestrator puts it in `<run>/sector_calls_score.md`).

## Which sectors get an entry
A sector is a group of businesses whose demand and profits move on the same drivers; it maps to one or more of screener's industry labels (`industries`) and may be narrower than any of them (e.g. "power transmission equipment" inside "Heavy Electrical Equipment"). Give an entry to:
1. every industry cluster in `sector_clusters.csv` with 5+ queued companies and an over-representation of 1.5x or more, or a z-score of 2 or more;
2. every sector that holds a holding;
3. every preferred sector in rule 21;
4. any sector with fresh official forward evidence (a newly notified policy, budget line, tariff or capacity plan) even if few companies are queued yet.
Every other queued company falls under "other" (rank last).

## Each entry (in `sector_map.md` in plain English, and in `sectors.json`)
1. **name, industries** (the labels it covers), sub-sectors, and **overrides**: holdings and companies whose label is a catch-all ("Industrial Products", "Other …") or spans several sectors, classified from what they actually do (`data/companies/<SYM>/scr/overview.json` about text; the latest annual report or presentation where that is unclear). The gate confirms each company's sector later.
2. **Tailwind kind:** demand or policy growth; value migration (profit pool moving to this sector or business model from another); capital-cycle turn (supply leaving or capex starved while demand holds); or none.
3. **Forward evidence**, each item with its number, date and source. Official sources only (rule 16): notified policy and gazette notifications, Union Budget documents, PIB, ministry and regulator data (RBI, SEBI, CEA, MNRE, MoD, MeitY, DPIIT, TRAI, IRDAI and the like), order books and capex plans filed on the exchanges by the sector's companies, capacity against demand from official data. Named expert or institutional research (person or firm and date) only as support, never alone; news only as a pointer to the official source. Anything else is an "unsourced view" and is kept out of the rank.
4. **Expected duration** with dates (from when to when, and why: the policy's term, the order books' execution period, the capacity gap's closing date).
5. **Discovery stage:** undiscovered / early / recognised / crowded, from S4's numbers (`sector_stage.csv` with `--sectors`); give the reason wherever you differ from the suggested stage.
6. **Profit-capture test:** does demand growth reach the sector's profits? Supply response (announced capacity against demand growth), pricing power (pass-through of costs, margin history in past upswings), consolidation (share of the top few). Verdict: captures / partly / doesn't, with the evidence.
7. **Headwinds** now and upcoming (regulatory risk, price and commodity cycles, overcapacity, import competition, customer concentration, tariff or trade risk, technology change), sourced as in 3.
8. **What would end it**, and **4-6 dated markers**: each {id, text, metric, where to check it, threshold or expected event, due date, check: "script" when `marker_check.py` can test it from saved data (the metric names it supports are in `runs/new_scripts_spec.md`), else "manual"}. A marker is something observable on a date: a policy still in force, an order-inflow figure in the sector's filings, a capacity commissioning, a price or margin level.
9. **Horizon supported** (short ~1-2 years, medium ~3-5, long 5-7+), from the expected duration; the analysis sets each company's own horizon from this and its own visibility (`process/investing_rules.md`).
10. **Rank** (the order of work): strongest dated forward evidence, longest remaining duration, earlier stage and a "captures" verdict first; no tailwind last.
11. **Playbook:** yes when screen survivors cluster here (item 1 above) or the forward evidence is strong, and no current playbook exists in `runs/playbooks/<sector>/` (current = written within 12 months and none of the sector's markers broken since); say why.
12. **Call date** (today) and, in review, what changed since the last call.

## Review (a full run with a previous map, and recheck mode)
- For each existing entry, check every marker due by now: "script" ones from `<run>/marker_check.csv` (`marker_check.py --sectors`), "manual" ones against their named source. Record each state (held / broken / not yet due) with the date and evidence in `sectors.json`.
- A broken marker: rewrite the entry (or mark the tailwind ended), and put the sector and the reason at the top of your reply; the orchestrator tells the user, marks the sector's companies for re-analysis, and in recheck mode proposes a full run for that sector.
- Recheck mode: review only markers that are due or whose script state changed; add no new sector unless a major policy was notified (say so in your reply: it triggers a full run).
- Full-run review: also run "Which sectors get an entry" again and update stages from the new S4 numbers. Keep calls honest: never reword a broken marker as held, and state in `sector_map.md` how the last calls fared (from the score file).

## Output
- `<run>/sector_map.md`: one section per sector with the items above and their sources; then the order of work (sectors by rank with their queued companies and holdings), the playbook choices, the past calls' hit rate, and open questions.
- `<run>/sectors.json` (python, ensure_ascii=False): `{"as_of": date, "run": "<FYyyQn>", "sectors": [{"id", "name", "industries", "sub_sectors", "overrides": {sym: reason}, "kind", "evidence": [{"claim", "value", "date", "source", "url"}], "start", "end", "duration_why", "stage", "stage_reason", "capture", "capture_evidence", "headwinds": [..], "ends_if", "markers": [{"id", "text", "metric", "where", "op", "threshold", "event", "due", "check", "state", "state_date", "state_evidence"}], "horizon", "rank", "playbook", "playbook_why", "call_date", "changed"}]}`.

Then the orchestrator runs `python -I tools/scripts/sector_order.py` (writes `<run>/sector_of.tsv` and reorders the gate batches not yet run) and `python -I tools/scripts/sector_calls.py log` (logs every new or changed call in `runs/sector_calls.csv`).

Reply with one line per sector: name, kind, stage, horizon, rank, playbook yes/no, markers changed; then anything you couldn't source.
