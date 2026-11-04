# F5: sector map (Opus medium helper)

## Sector map (helper)
Build the sector map that decides which companies are analysed first. Write only the files named below. Working directory: the project root (PowerShell). The run folder and the list of gate survivors and holdings are in your brief. If the previous quarter's run folder has a `sector_map.md`, review and update it rather than rebuild it.

Inputs: the company list in your brief; `process/investing_rules.md` rule 21 (the user's sector preferences).

1. Classify every company into a sector and sub-sector from what it actually does: its gate file (`<run>/gate/<SYM>.json`), the business description in its latest annual report or presentation (already in `data/companies/<SYM>/` or downloadable from the exchange links in its saved screener document list), and screener's "about" text (`data/companies/<SYM>/scr/overview.json`; run `scr_company.py <SYM> --only overview` if missing). A data provider's sector label is often too broad. Save `<run>/sector_of.tsv`: sym, name, held, sector, sub_sector, end_markets, tier.
2. For each sector present, and each preferred sector, write in `<run>/sector_map.md`:
   - tailwinds now and upcoming (next 1-5 years), with numbers and dates where they exist: government capex and budget lines, PLI and other notified schemes, policy and regulation, demand data, capacity shortfalls, import substitution;
   - headwinds now and upcoming: regulatory risk, price/commodity cycles, overcapacity, import competition, customer concentration, tariff or trade risks, technology disruption;
   - where the sector is in its cycle, and what would change the view;
   - a tier: 1 = strong tailwind and no major headwind; 2 = neutral or mixed; 3 = major headwind.
   Every tailwind and headwind needs a source: official ones first (Union Budget documents, PIB, ministry and regulator notifications and data: RBI, SEBI, CEA, MNRE, MoD, MeitY, DPIIT, TRAI, IRDAI), then reputed, named expert or institutional research (person or firm and date). News articles only as pointers to the official source. Use WebSearch/WebFetch. Mark anything unsourced as "unsourced view" and keep it out of the tier.
3. Fill the tier column, and end `sector_map.md` with companies per tier and open questions.

Reply with: each sector and its tier on one line, companies per tier, and anything you couldn't source.
