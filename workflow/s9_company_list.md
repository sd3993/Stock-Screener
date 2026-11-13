# S9: company list; S10.0: fetch scripts (scripts; both modes)

## S9: company list
`python -I scripts/run.py list` (mode from `progress.md`) writes `<run>/company_list.csv` (sym, name, held, sector, sector_rank, horizon, order, why) and adds every company to `status.csv` at S10, state queued (never twice). Its `--help` (`run.py list --help`) has the exact rules:
- **full mode** (after the last S8R and `sectors.py order --from-gate`): every holding (from `holdings.csv`) plus every gate survivor (NEXT in `<run>/gate/decisions.csv`). Order: holdings first; then survivors by their sector's rank in `sectors.json` (tailwind sectors first, "other" last), and within a sector by the gate's best-horizon CAGR, highest first. No survivor is dropped for its sector. A survivor or holding without a `sector_of.tsv` row stops it: re-run `sectors.py order --from-gate`.
- **recheck mode** (after S1 and S5's review): every holding plus every company with a thesis (`runs/companies/<SYM>/thesis.json`), and any ticker in the sheet's Data tab that has none (read through `gws` when the sheet can be read; otherwise it says so and works from the theses and holdings alone). Order: holdings first; then companies whose sector had a marker break; then the rest by sector rank. A company with no thesis is marked "no thesis: re-analyse".

## S10.0: fetch scripts (one company at a time, before its S11 or S12)
Run the two fetch scripts the fetch subagent's file names (`/workflow/s12_fetch.md`), in its order (if screener.in can't be reached: `/sources/screener.md`). In full mode tell the S12 subagent in its brief that they ran. In recheck mode run S11 (`s11_marker_check.md`) next.
