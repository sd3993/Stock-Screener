# S5R: sector map recheck checklist (deep tier, run per `/workflow/recheck.md`)

Work files: `<run>/sector_map.md` and `<run>/sectors.json` (or the previous recheck's versions); your output: `sector_map_rc<N>.md` and `sectors_rc<N>.json`. Read `/workflow/s5_sector_map.md` and `/principles/sector_rules.md` first.

1. **Coverage:** every cluster, holding sector and preferred sector the sector standard names has an entry; nothing in "other" belongs in a sector.
2. **Classification:** each override (catch-all labels, holdings) against what the company actually does (annual report or presentation business description, screener's "about" text).
3. **Sources:** each forward-evidence item and headwind meets the sector standard's sourcing (the news and events rule); anything unsourced is marked and kept out of the rank.
4. **Contrary evidence** for each entry: headwinds the map missed for a tailwind sector (policy reversals, overcapacity, import competition, price cycles, supply response that will cap profits) and tailwinds it missed for a "none" sector.
5. **Stage and capture:** the stage follows from S4's numbers (or the reason for differing holds); the profit-capture verdict follows from its evidence.
6. **Markers:** each meets the sector standard (count, observable on its due date from a named source); "script" markers use a metric `thesis.py check` supports (its `--help`); review states match the evidence.
7. **Rank and playbook choices** follow from the entries per the sector standard.
