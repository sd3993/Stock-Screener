# S9: company list; S10.0: fetch scripts (scripts; both modes)

## S9: company list
`python -I tools/scripts/company_list.py` (to write; `runs/new_scripts_spec.md`) writes `<run>/company_list.csv` (sym, name, held, sector, sector_rank, horizon, order, why) and adds every company to `status.csv` at S10, state queued. Until the script exists, a light-tier helper builds the same file from the same rules:
- **full mode** (after the last S8R and `sector_order.py --from-gate`): every holding (from `holdings.csv`) plus every gate survivor (NEXT in `<run>/gate/decisions.csv`). Order: holdings first; then survivors by their sector's rank in `sectors.json` (tailwind sectors first, "other" last), and within a sector by the gate's best-horizon CAGR, highest first. No survivor is dropped for its sector.
- **recheck mode** (after S1 and S5's review): every holding plus every ticker in the sheet's Data tab (read through `gws`, `tools/tools.md`), each with its thesis file `runs/theses/<SYM>.json` if it has one. Order: holdings first; then companies whose sector had a marker break; then the rest by sector rank.

## S10.0: fetch scripts (one company at a time, before its S11 or S12)
Run the two fetch scripts named in `s12_fetch.md` step 2, in that order. In full mode tell the S12 helper in its brief that they ran. In recheck mode run S11 (`s11_marker_check.md`) next.
