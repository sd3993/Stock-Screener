# Sector rules: the sector map, discovery stage, thesis markers and playbooks

Standards for sector work: what the sector map is for and what each entry holds, what the discovery stage means, what a thesis marker must be, how businesses are typed, what a playbook finding must pass, and the caveats every sector call and playbook finding states. They build on `/principles/investing_rules.md`; how each step does the work is in `/workflow/WORKFLOW.md`.

## Market-wide screening and the map's role
- **Screening is always market-wide, never sector-only.** Why (evidence from the playbook base data, `data/playbook/sector_test.md`): multibaggers cluster by industry only moderately (the top-20% industries held 47% of 3x-in-5-years winners against 38% by chance); a company with high EPS growth in a low-growth industry still reached 3x 48% of the time against 56% in a high-growth one; and no backward-looking industry figure predicted which industries would produce winners (rank correlation about 0 from 2016).
- **The map frames the work:** it orders companies through the gate and the analysis (tailwind sectors first), sets the horizon and re-rating case each company's thesis starts from, and chooses which sectors get a playbook (S6-S7). It never removes a company: screening stays market-wide, and a company in a sector with no tailwind is still gated and analysed, only later in the order.

## Sectors and classification
- **A sector** is a group of businesses whose demand and profits move on the same drivers; it maps to one or more of screener's industry labels (`industries`) and may be narrower than any of them (e.g. "power transmission equipment" inside "Heavy Electrical Equipment").
- **Industry labels** are screener's copy of NSE's industry classification: a coarse hint that S5 and the gate correct from what each company actually does.
- **Which sectors get an entry:**
  - every industry cluster in `sector_clusters.csv` with 5+ queued companies and an over-representation of 1.5x or more, or a z-score of 2 or more (the cluster criterion);
  - every sector that holds a holding;
  - every preferred sector in the sector preferences rule;
  - any sector with fresh official forward evidence (a newly notified policy, budget line, tariff or capacity plan) even if few companies are queued yet.

  Every other queued company falls under "other" (rank last).

## What each entry holds (in `sector_map.md` in plain English, and in `sectors.json`)
- **Name, industries** (the labels it covers), sub-sectors, and **overrides**: holdings and companies whose label is a catch-all ("Industrial Products", "Other …") or spans several sectors, classified from what they actually do (`data/companies/<SYM>/scr/overview.json` about text; the latest annual report or presentation where that is unclear). The gate confirms each company's sector later.
- **Tailwind kind:** demand or policy growth; value migration (profit pool moving to this sector or business model from another); capital-cycle turn (supply leaving or capex starved while demand holds); or none.
- **Forward evidence**, each item with its number, date and source. Official sources only (the news and events rule): notified policy and gazette notifications, Union Budget documents, PIB, ministry and regulator data (RBI, SEBI, CEA, MNRE, MoD, MeitY, DPIIT, TRAI, IRDAI and the like), order books and capex plans filed on the exchanges by the sector's companies, capacity against demand from official data. Named expert or institutional research (person or firm and date) only as support, never alone; news only as a pointer to the official source. Anything else is an "unsourced view" and is kept out of the rank.
- **Expected duration** with dates (from when to when, and why: the policy's term, the order books' execution period, the capacity gap's closing date).
- **Discovery stage:** undiscovered / early / recognised / crowded, from S4's numbers (`sector_stage.csv` with `--sectors`); give the reason wherever you differ from the suggested stage.
- **Profit-capture test:** does demand growth reach the sector's profits? Supply response (announced capacity against demand growth), pricing power (pass-through of costs, margin history in past upswings), consolidation (share of the top few). Verdict: captures / partly / doesn't, with the evidence.
- **Headwinds** now and upcoming (regulatory risk, price and commodity cycles, overcapacity, import competition, customer concentration, tariff or trade risk, technology change), sourced as forward evidence is.
- **What would end it**, and **4-6 dated markers**: each {id, text, metric, where to check it, threshold or expected event, due date, by (true when the line is to be reached by the due date rather than held every quarter), check: "script" when `thesis.py check` can test it from saved data (the metrics it supports are listed in `scripts/thesis.py check --help`; sector markers may also use `pe_pct` and `ret_1y` from `sector_stage.csv`), else "manual"}.
- **Horizon supported** (short ~1-2 years, medium ~3-5, long 5-7+), from the expected duration; the analysis sets each company's own horizon from this and its own visibility (`/principles/investing_rules.md`).
- **Rank** (the order of work): strongest dated forward evidence, longest remaining duration, earlier stage and a "captures" verdict first; no tailwind last.
- **Playbook:** yes when screen survivors cluster here (the cluster criterion) or the forward evidence is strong, and no current playbook exists in `data/playbook/sectors/<sector>/`; say why.
- **Call date** (today) and, in review, what changed since the last call.

## Discovery stage
- The stage describes how priced-in a sector is (sizing, how much re-rating a thesis may assume); tested on the playbook base data it did not reliably predict which industries produced winners (`data/playbook/stage_test.md`), so it never ranks or picks sectors.

## Markers
- **What a marker is:** something observable on a date: a policy still in force, an order-inflow figure in the sector's filings, a capacity commissioning, a price or margin level.
- **Keep calls honest:** never reword a broken marker as held.
- **A company's thesis markers** (beyond the count and levels the exit rules set): at least one sector-level (copying the id of the sector marker it rests on) and at least three company-level (e.g. quarterly revenue or profit growth against a floor, margin band, order inflow, capacity commissioning by a date, cash conversion, promoter holding or pledge), each showing the thesis holding or breaking. Thresholds are set where a miss would genuinely change the case, not at the first wobble.

## Business type (when a sector spans different economics)
Classify each company by what it actually does and what drives its results, never by a provider's label. Keep the type list short and economic, e.g. branded consumer, specialty manufacturer (engineered/B2B products), contract manufacturer/CDMO, capital goods and order-book businesses, EPC/infrastructure contractor, commodity producer or processor, lender, insurer/AMC/broker/platform, IT and knowledge services, healthcare services, pharma (generic/specialty/API), retail and distribution, real-estate developer, regulated utility, conglomerate/holding company; add a type only when companies don't fit (in `data/playbook/business_types/new_types*.md`).

## Playbooks
- **Current:** a playbook is current when written within 12 months and none of the sector's markers broken since; a current playbook is reused across runs.
- **No hindsight:** an episode study reads, for each stage, only documents dated before it; older years only from what was filed then.
- **Pattern tests** (short form; every pattern a playbook proposes):
  - **Point in time:** measured only from data published before the episode's start (results from their filing date, or quarter end + 45 days, + 60 for Q4; prices and P/E from the chart series on that date; `mb_features.py --help`). A pattern resting on a figure restated later is not used.
  - **Lift:** the pattern's share among companies that captured the tailwind, divided by its share among the sector's companies that didn't, on the same start date. Proposed only with a lift of 1.5 or more and a frequency of 50% or more among the captured; raw values are never compared across dates.
  - **Reason required:** a mechanism (earnings growth plus re-rating, reinvestment at high returns, operating leverage, supply discipline, balance-sheet repair) backed by the episode studies or `experts.md`. A strong number with no reason is reported as "possibly chance" and not proposed.
  - **Out of sample:** found on episodes starting before 2016, held unchanged on later ones (or on another sector's episodes of the same tailwind kind); thresholds checked at nearby values. The number of patterns tried is reported with the results. Infrequent patterns (turnarounds, spin-offs, windfalls) stay low-weight situational notes.

## Caveats (stated with every sector call and playbook finding)
- **Survivorship:** screener's screens list only listed companies; delisted and merged names come from the delisted list and whatever screener still has.
- **Labels:** industry labels are today's NSE classification (screener's copy), not the one at a past date.
- **Old fundamentals:** screener's statements cover about 12 years; before them only chart features (growth, P/E, size, price) cover every company, and annual-report statements cover only what was parsed (`/workflow/ar_statements.md`).
- **Forward evidence only:** backward industry figures did not predict winning industries in the playbook base data, so a sector call rests on official forward evidence and is scored later, not trusted on its numbers.
