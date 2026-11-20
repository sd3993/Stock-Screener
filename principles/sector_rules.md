# Sector rules: the sector map, emerging sectors, discovery stage and thesis markers

Standards for sector work; they build on `/principles/investing_rules.md`.

## Sector focus and the map's role
- **Screening is market-wide; the deep work is focused:** screens and triage cover the whole market; the gate and the analysis go mostly to the focus set, so the usage saved goes into analysing those companies better.
- **Focus sectors:** map entries with a tailwind (kind other than none) whose expected duration ends at least 3 years after the map's date. A shorter or unevidenced tailwind is not a focus sector.
- **The focus set** (queued for the gate): companies mapped to a focus sector; the emerging entries' emerging companies and participants; the focus sectors' suppliers (below); holdings, always. **Reserve:** a queued company outside the focus set with any earnings evidence (E1 acceleration, E2 re-rating candidate, E3 sustained growth or E4 turnaround); like every company, it passes the gate and the analysis only on filed evidence of action (orders, commissioned capacity, delivered results), never on stories or plans without action. The reserve is gated only after the focus set has been gated and analysed, and only while the List and the holdings kept fall short of the positions the capital allows at the target size (the position size and count rule): then the next highest-headroom reserve companies, a batch at a time, until they don't. Every other queued company is not gated in the run (recorded as outside the focus).
- **Order of work:** the focus set by rank, crowded sectors last; crowded sectors are still gated, since a company whose price is ahead of its growth can go on the watchlist (a price watch) until the price falls or earnings catch up.
- **The map's role:** it decides the focus set and the gate order, gives the sector evidence a company's thesis may draw on, finds emerging sectors and businesses and the focus sectors' suppliers, and tracks upcoming themes. It sets no company's holding period: every company is analysed on its own growth and visibility.

## Sectors and classification
- **A sector** is a group of businesses whose demand and profits move on the same drivers; it maps to one or more of screener's industry labels (`industries`) and may be narrower than any of them (e.g. "power transmission equipment" inside "Heavy Electrical Equipment").
- **Industry labels** are screener's copy of NSE's industry classification: a coarse hint that S5 and the gate correct from what each company actually does.
- **Which sectors get an entry:**
  - every industry cluster in `sector_clusters.csv` with 5+ queued companies and an over-representation of 1.5x or more, or a z-score of 2 or more (the cluster criterion);
  - every sector that holds a holding;
  - every preferred sector in the sector preferences rule;
  - any sector with fresh official forward evidence (a newly notified policy, budget line, tariff or capacity plan) even if few companies are queued yet;
  - every **emerging** sector or business: a problem that an official source quantifies (import dependence, a capacity shortfall, a notified or draft policy, a regulator's consultation paper); with **proven demand**, someone already paying for the solution (imports being replaced, tenders awarded, firm orders, offtake contracts), not only a policy target or a projected market size; that at least one listed company is solving with filed evidence (pilot orders, approvals, capex, a new segment line); and that is not priced in (discovery stage undiscovered or early, and no cluster in the screens). An **unsolved** problem, one that today's supply doesn't meet (a shortfall or a high import share in official data), is preferred and ranks higher, but is not required. It stays emerging until its stage reaches recognised. Its emerging companies and participants (below) are queued for the gate even when no screen caught them.

  Every other queued company falls under "other" (rank last, and outside the focus unless it is in the reserve).

## Emerging companies and emerging businesses
- **Emerging company:** all or nearly all of its business is the emerging one (any older business is small or being wound down). It sits in the emerging entry as an override, and counts toward the emerging cap (`/principles/investing_rules.md`, the allocation and rebalancing rule).
- **Participant** (an established company with an emerging business): it belongs to the sector of its main business (where most of its profit comes from today), counts toward that sector's stock limit and trim line, and is sized like any company, outside the emerging cap. The emerging entry lists it as a participant, so it is queued for the gate and its emerging business may draw on the entry's evidence.
- **A participant's thesis** may rest on the established business, the emerging one or both, whichever is strongly promising; each part the thesis relies on gets its own markers. The emerging part enters the base case only as far as filed evidence backs it (firm orders, commissioned capacity, an offtake contract); plans and pilots stay upside only. When most of the base-case return comes from the emerging part, evidence quality is at most Medium.

## Suppliers (pick-and-shovel companies)
- **Found by backtracking from the focus sector, not by the supplier's own label:** for each focus sector, list what its growth needs (materials, components, equipment, services, testing and certification), then find the listed companies making those, whatever their own industry label or sector.
- **Eligible only when the share is significant:** the focus sectors (one or several together) take about a third or more of the supplier's current revenue, or most of its planned growth (filed capacity or guidance aimed at them). A small fraction does not qualify. The share comes from filed evidence (segment reporting, the annual report's customer or end-market split, the call transcript); an estimate says so and how it was made.
- **Sector and sizing:** like a participant, a supplier belongs to its main business's sector, counts toward that sector's limits, and is sized like any company; the focus entry lists it under `suppliers` with its share and evidence.
- **Tied to the sector's demand, not to its winners:** a supplier rides the focus sectors' total build-out whichever companies win share in them.
- **Risks are sized, not avoided:** the analysis sizes each: the build-out ending (orders fall when the customers' build-out ends: the focus sector's end date against the projection length); pass-through (revenue moving with a commodity price rather than volume: growth is judged on volume and per-unit margin); the focus share and its trend; customer concentration and bargaining power; capacity other suppliers are adding.

## What each entry holds (in `sector_map.md` in plain English, and in `sectors.json`)
- **Name, industries** (the labels it covers), sub-sectors, and **overrides**: holdings and companies whose label is a catch-all ("Industrial Products", "Other …") or spans several sectors, classified from what they actually do (`data/companies/<SYM>/scr/overview.json` about text; the latest annual report or presentation where that is unclear). The gate confirms each company's sector later.
- **Tailwind kind:** demand or policy growth; value migration (profit pool moving to this sector or business model from another); capital-cycle turn (supply leaving or capex starved while demand holds); or none.
- **Emerging:** yes or no; for yes, the problem with its official figure, date and source, the proven demand with its source, whether the problem is unsolved, each emerging company (an override) and each participant (its sector from its main business) with its filed evidence.
- **Suppliers** (focus sectors): each supplier with what it supplies, its focus share and the evidence.
- **Forward evidence**, each item with its number, date and source. Official sources only (the news and events rule): notified policy and gazette notifications, Union Budget documents, PIB, ministry and regulator data (RBI, SEBI, CEA, MNRE, MoD, MeitY, DPIIT, TRAI, IRDAI and the like), order books and capex plans filed on the exchanges by the sector's companies, capacity against demand from official data. Named expert or institutional research (person or firm and date) only as support, never alone; news only as a pointer to the official source. Anything else is an "unsourced view" and is kept out of the rank.
- **Expected duration** with dates (from when to when, and why: the policy's term, the order books' execution period, the capacity gap's closing date).
- **Discovery stage** (below), from S4's numbers (`sector_stage.csv` with `--sectors`); give the reason wherever you differ from the suggested stage.
- **Profit-capture test:** does demand growth reach the sector's profits? Supply response (announced capacity against demand growth), pricing power (pass-through of costs, margin history in past upswings), consolidation (share of the top few). Verdict: captures / partly / doesn't, with the evidence.
- **Supply balance:** tight / balanced / surplus (with the date demand is expected to absorb it), from official or filed capacity against demand. A surplus does not exclude a sector: earnings can still grow when demand outgrows capacity; it ranks lower the later it clears.
- **Headwinds** now and upcoming (regulatory risk, price and commodity cycles, overcapacity, import competition, customer concentration, tariff or trade risk, technology change), sourced as forward evidence is.
- **What would end it**, and **4-6 dated markers**: each {id, text, metric, where to check it, threshold or expected event, due date, by (true when the line is to be reached by the due date rather than held every quarter), check: "script" when `thesis.py check` can test it from saved data (the metrics it supports are listed in `scripts/thesis.py check --help`; sector markers may also use `pe_pct` and `ret_1y` from `sector_stage.csv`), else "manual"}.
- **Rank** (the order of work): strongest dated forward evidence, longest remaining duration, tight supply and a "captures" verdict first; a surplus that clears late ranks lower; no tailwind last.
- **Call date** (today) and, in review, what changed since the last call.

## Upcoming themes
- **What they are:** demand or policy themes that may become a tailwind but are too early for an entry (no proven demand yet, approvals pending, technology or programme not yet delivering). Catching them early is the point: the aim is to find such companies before they are widely discovered, at lower prices.
- **What each holds:** the problem with its official figure and source; what would make it an entry (2-4 dated markers); its listed companies, each with its filed link and whether the link is material (the theme, if it succeeds, would be a significant part of the company's revenue or planned growth, as for suppliers).
- **Review:** every full run checks each theme's markers; a theme becomes an entry once its markers are met and the entry criteria hold. Companies with a material link go on the watchlist as a theme watch (no analysis yet); an immaterial link (a large company for which it is a small fraction) is only noted.

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
