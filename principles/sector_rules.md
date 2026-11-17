# Sector rules: the sector map, emerging sectors, discovery stage and thesis markers

Standards for sector work; they build on `/principles/investing_rules.md`.

## Market-wide screening and the map's role
- **Screening is always market-wide, never sector-only:** a company outside every tailwind sector can still multiply on its own growth.
- **The map's role:** it orders companies through the gate (tailwind sectors first), gives the sector evidence a company's thesis may draw on, and finds emerging sectors and businesses. It never removes a company and sets no company's holding period: one in a sector with no tailwind, or in a low-growth industry, is still queued, gated and analysed on its own growth and visibility.

## Sectors and classification
- **A sector** is a group of businesses whose demand and profits move on the same drivers; it maps to one or more of screener's industry labels (`industries`) and may be narrower than any of them (e.g. "power transmission equipment" inside "Heavy Electrical Equipment").
- **Industry labels** are screener's copy of NSE's industry classification: a coarse hint that S5 and the gate correct from what each company actually does.
- **Which sectors get an entry:**
  - every industry cluster in `sector_clusters.csv` with 5+ queued companies and an over-representation of 1.5x or more, or a z-score of 2 or more (the cluster criterion);
  - every sector that holds a holding;
  - every preferred sector in the sector preferences rule;
  - any sector with fresh official forward evidence (a newly notified policy, budget line, tariff or capacity plan) even if few companies are queued yet;
  - every **emerging** sector or business: a problem that an official source quantifies (import dependence, a capacity shortfall, a notified or draft policy, a regulator's consultation paper), that at least one listed company is solving with filed evidence (pilot orders, approvals, capex, a new segment line), and that is not priced in (discovery stage undiscovered or early, and no cluster in the screens). It stays emerging until its stage reaches recognised. Its companies are queued for the gate even when no screen caught them.

  Every other queued company falls under "other" (rank last).

## What each entry holds (in `sector_map.md` in plain English, and in `sectors.json`)
- **Name, industries** (the labels it covers), sub-sectors, and **overrides**: holdings and companies whose label is a catch-all ("Industrial Products", "Other …") or spans several sectors, classified from what they actually do (`data/companies/<SYM>/scr/overview.json` about text; the latest annual report or presentation where that is unclear). The gate confirms each company's sector later.
- **Tailwind kind:** demand or policy growth; value migration (profit pool moving to this sector or business model from another); capital-cycle turn (supply leaving or capex starved while demand holds); or none.
- **Emerging:** yes or no; for yes, the problem with its official figure, date and source, and each listed company solving it (as an override) with its filed evidence.
- **Forward evidence**, each item with its number, date and source. Official sources only (the news and events rule): notified policy and gazette notifications, Union Budget documents, PIB, ministry and regulator data (RBI, SEBI, CEA, MNRE, MoD, MeitY, DPIIT, TRAI, IRDAI and the like), order books and capex plans filed on the exchanges by the sector's companies, capacity against demand from official data. Named expert or institutional research (person or firm and date) only as support, never alone; news only as a pointer to the official source. Anything else is an "unsourced view" and is kept out of the rank.
- **Expected duration** with dates (from when to when, and why: the policy's term, the order books' execution period, the capacity gap's closing date).
- **Discovery stage** (below), from S4's numbers (`sector_stage.csv` with `--sectors`); give the reason wherever you differ from the suggested stage.
- **Profit-capture test:** does demand growth reach the sector's profits? Supply response (announced capacity against demand growth), pricing power (pass-through of costs, margin history in past upswings), consolidation (share of the top few). Verdict: captures / partly / doesn't, with the evidence.
- **Headwinds** now and upcoming (regulatory risk, price and commodity cycles, overcapacity, import competition, customer concentration, tariff or trade risk, technology change), sourced as forward evidence is.
- **What would end it**, and **4-6 dated markers**: each {id, text, metric, where to check it, threshold or expected event, due date, by (true when the line is to be reached by the due date rather than held every quarter), check: "script" when `thesis.py check` can test it from saved data (the metrics it supports are listed in `scripts/thesis.py check --help`; sector markers may also use `pe_pct` and `ret_1y` from `sector_stage.csv`), else "manual"}.
- **Rank** (the order of work): strongest dated forward evidence, longest remaining duration and a "captures" verdict first; no tailwind last.
- **Call date** (today) and, in review, what changed since the last call.

## Discovery stage
- The stage (defined in `/principles/investing_rules.md`) describes how priced-in a sector is. It never ranks or picks sectors; it tells emerging entries apart and sizes positions.

## Markers
- **What a marker is:** something observable on a date: a policy still in force, an order-inflow figure in the sector's filings, a capacity commissioning, a price or margin level.
- **Keep calls honest:** never reword a broken marker as held.
- **A company's thesis markers** (beyond what the exit rules set): at least three company-level (e.g. trailing-four-quarter revenue growth against a floor, order book or inflow, capacity commissioning by a date, guidance delivered, margin band, cash conversion, promoter holding or pledge), each showing the thesis holding or breaking; and one sector-level (copying the id of the sector marker it rests on) when the company's sector has a map entry with markers. Thresholds are set where a miss would genuinely change the case, not at the first wobble.

## Caveats (stated with every sector call)
- **Survivorship:** screener's screens list only companies listed today.
- **Labels:** industry labels are today's NSE classification (screener's copy), not the one at a past date.
- **Forward evidence only:** a sector call rests on official forward evidence and is scored later, never trusted on its backward numbers.
