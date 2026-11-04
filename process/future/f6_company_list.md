# F6: company list (F6.1) and fetch scripts (F6.2), run by the orchestrator

## F6.1: company list (after the last F5R)
Write `<run>/company_list.csv` (sym, name, held, sector, tier, order): every holding (from `holdings.csv`) plus every gate survivor (NEXT in `<run>/gate/decisions.csv`). Order: holdings first, then tier-1 sectors, then tier 2; tier-3 companies only if exceptional (say why in `progress.md`). Add every company to `status.csv` at F6.2, state queued.

## F6.2: fetch scripts (one company at a time, before its F7 helper)
Run the two fetch scripts named in `f7_fetch.md` step 2, in that order, and tell the F7 helper in its brief that they ran.
