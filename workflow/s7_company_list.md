# S7: company list; S8.0: fetch scripts (scripts; both modes)

## S7: company list
`python -I scripts/run.py list` (mode from `progress.md`) writes `<run>/company_list.csv` (sym, name, held, sector, sector_rank, years, order, why) and adds every company to `status.csv` at S8, state queued (never twice). Its `--help` (`run.py list --help`) has the exact rules:
- **full mode** (after the last S6R and `sectors.py order --from-gate`): every holding (from `holdings.csv`) plus every gate survivor (NEXT in `<run>/gate/decisions.csv`). Order: holdings first; then survivors by the gate's estimated CAGR, highest first (sector rank only breaks ties). No survivor is dropped for its sector. A survivor or holding without a `sector_of.tsv` row stops it: re-run `sectors.py order --from-gate`.
- **recheck mode** (after S1 and S5's review): every holding plus every company with a thesis that is not a reject (`runs/companies/<SYM>/thesis.json`; watchlist names included), and any ticker in the sheet's Data tab that has none (read when the sheet can be read; otherwise it says so and works from the theses and holdings alone). Order: holdings first; then companies whose sector had a marker break; then the rest by sector rank. A company with no thesis is marked "no thesis: re-analyse".

## S8.0: fetch scripts (one company at a time, before its S9 or S10)
Run the two fetch scripts the fetch subagent's file names (`/workflow/s10_fetch.md`), in its order (if screener.in can't be reached: `/sources/screener.md`). In full mode tell the S10 subagent in its brief that they ran. In recheck mode run S9 (`s9_marker_check.md`) next.
