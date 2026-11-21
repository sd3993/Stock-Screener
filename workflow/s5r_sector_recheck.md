# S5R: sector map recheck checklist (deep tier, run per `/workflow/recheck.md`)

Work files: `<run>/sector_map.md` and `<run>/sectors.json` (or the previous recheck's versions); your output: `sector_map_rc<N>.md` and `sectors_rc<N>.json`. Read `/workflow/s5_sector_map.md` and `/principles/sector_rules.md` first.

1. **Coverage:** every cluster, holding sector, preferred sector and emerging sector or business the sector standard names has an entry; nothing in "other" belongs in a sector; an entry that covers the same business as one in the previous map has kept its id.
2. **Classification:** each override (catch-all labels, holdings) against what the company actually does (annual report or presentation business description, screener's "about" text).
3. **Sources:** each forward-evidence item and headwind meets the sector standard's sourcing (the news and events rule); anything unsourced is marked and kept out of the rank.
4. **Contrary evidence** for each entry: headwinds the map missed for a tailwind sector (policy reversals, overcapacity, import competition, price cycles, supply response that will cap profits) and tailwinds it missed for a "none" sector.
5. **Stage and capture:** the stage follows from S4's numbers (or the reason for differing holds); the profit-capture verdict follows from its evidence, which cites filed or official capacity and entrant evidence or says none exists.
6. **Markers:** each meets the sector standard (count, observable on its due date from a named source); "script" markers use a metric `thesis.py check` supports (its `--help`); review states match the evidence.
7. **Rank** follows from the entries per the sector standard.
8. **Emerging entries:** each meets every emerging test of the sector standard from its sources, proven demand included; each listed company's part rests on its own filings, not a press claim; each is rightly an emerging company or a participant, and each participant sits in its main business's sector; every filing a participant made after the award or plan its part rests on is read, since a rescission or cancellation can sit under a generic headline; contrary evidence that the problem is already priced in (stage, institutional holding, P/E against the company's own history).
9. **Suppliers:** every focus sector's suppliers were looked for by backtracking (its inputs listed and tested); each listed supplier's focus share meets the share test on filed evidence (firm orders only in an order-book share), counting exports only into a global entry's same demand.
10. **Scope:** each focus entry's domestic or global scope rests on its evidence.
11. **Supply balance:** each rests on capacity-against-demand evidence.
12. **Upcoming themes:** each has markers, and each company's material or immaterial call is right.
