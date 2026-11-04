# The process: map, order of work and resuming

Read by the orchestrator (any session that runs or resumes a run). Where each data item comes from, and what is already settled about each source: the top two sections of `tools/tools.md`. Helpers get only their own phase file plus what it names. Standing instructions and working preferences: `CLAUDE.md`.

## In one picture
```
F1 holdings ─┐
F2 screens ──┴─> F3 triage ─> F4 gate (+F4R) ─> F5 sector map & company list (+F5R)
                                                   │
             ┌─────────────────────────────────────┘  one company at a time, in list order
             v
            F6 fetch ──changed?──no──> done for this run
             │ yes
             v
            F7 analysis ─> F7R1 ─> F7R2 ─> F8 sheet listing (batched)
             ^ NEW_RESULTS (max 2 loops)
                                      all companies done ─> F9 allocation (+F9R1, F9R2) ─> F9W sheet write
```

## Phases
screener.in (through the screener library in scripts: `scr_tool.py` for screens, `scr_company.py` for company data; `tools/tools.md`) is the main source, with NSE/BSE for the rest (`process/data_rules.md`). No phase needs Tapetide.

| # | Phase | Who | Model / effort | File | Output (in `runs/future/<FYyyQn>/` unless noted) | Done when |
|---|---|---|---|---|---|---|
| F1 | Holdings from Kite; run setup | orchestrator | (orchestrator's) | `f1_holdings.md` | `holdings.csv`, sheet's pending tab | holdings saved (or last ones kept, user told) |
| F2 | Market screens and the whole-market sweep | helper | Sonnet low | `f2_screens.md` | `screens/`, `universe.csv` | every screen and band page saved, totals match |
| F3 | Number triage and gate batches | script | none | `f3_triage.md` | `triage.csv`, `gate_batches.json` | every universe company and holding has a triage row |
| F4 | Gate, one batch of ~10 | helper | Opus medium | `f4_gate.md` | `gate/bNN.json`, `gate/<SYM>.json` | every company in the batch has a decision |
| F4R | Gate recheck | helper | Opus medium | `f4r_gate_recheck.md` | `gate/bNN_rc1.json` (rc2 if needed) | per `recheck.md` |
| F5 | Sector map and company list | helper (map), orchestrator (list) | Opus medium | `f5_sector_map.md` | `sector_map.md`, `sector_of.tsv`, `company_list.csv` | every listed company has a sector and tier |
| F5R | Sector map recheck | helper | Opus medium | `f5r_sector_recheck.md` | `sector_map_rc1.md` (rc2 if needed) | per `recheck.md` |
| F6 | Fetch one company | scripts + helper | Sonnet medium | `f6_fetch.md` | `data/companies/<SYM>/` (documents, `scr/`, `bse/`, `facts.json`) | reply `CHANGED: yes/no` |
| F7 | Deep analysis, one company | helper | Opus high | `f7_analysis.md` | `analysis/<SYM>/main.json`, `.md` | reply with buckets and EPS paths, or `NEW_RESULTS` |
| F7R | Analysis rechecks 1 and 2 | helper each | Opus medium (Opus high for an `unresolved` judgement call) | `f7r_analysis_recheck.md` | `analysis/<SYM>/recheck1.json`, `recheck2.json` (+ `.md`) | per `recheck.md` |
| F8 | Sheet listing, batch of agreed analyses | helper | Sonnet low | `f8_listing.md` | Data, Data Flags, pending tabs; `runs/future/verdict_history.csv` | every agreed analysis since the last listing is in the sheet |
| F9 | Allocation and holdings decision | helper | Opus medium | `f9_allocation.md` | `allocation/main.json` | decisions written with reasons |
| F9R | Allocation rechecks 1 and 2 | helper each | Opus medium | `f9r_allocation_recheck.md` | `allocation/recheck1.json`, `recheck2.json` | per `recheck.md` |
| F9W | Sheet write of the allocation | helper | Sonnet low | `f9_allocation.md` (part "write") | Holdings and Allocation tabs | rows match the last recheck exactly |

Orchestrator: Sonnet medium (Opus medium when judging a recheck conflict or a rule change; Opus high only when clearly needed, saying why). Every to-do list names each phase's model and effort (e.g. "F7 [Opus high]").

## Order of work
1. **Run setup and F1.** A run is named after the latest quarter that has ended (`FYyyQn`), even if not every company has declared it. Create `runs/future/<FYyyQn>/`, set the run in `tools/scripts/config.py` (or the `RUN` environment variable), and do F1. Best started after the quarter's results deadline (45 days after quarter end; 60 for Q4), so most companies are fetched once.
2. **F2 → F3 → F4 (+F4R) per batch → F5 (+F5R).** F2 and F1 are independent. F4 batches run one after another. Before each batch, the orchestrator runs `uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM>` for every company in it. Each batch's recheck runs before the next batch, and its learnings are applied first.
3. **Companies flow one at a time** through F6 → F7 → F7R1 → F7R2, in `company_list.csv` order (holdings first), so each company's learnings reach the next. Before F6 the orchestrator runs the fetch scripts named in `f6_fetch.md` step 2.
   - F6 replies `CHANGED: no` → that company is done for this run (status F8 done, note "no change").
   - F7 or a recheck replies `NEW_RESULTS` → back to F6 for that company alone, then restart F7. After 2 such loops, flag it (`acknowledgements.md`) and tell F7 to carry on with the data it has.
   - After F7R2: copy `recheck2.md` to `analysis/<SYM>/<SYM>.md` (the agreed analysis); apply its learnings and any sector-note proposals (listed for acknowledgement) before the next company.
4. **F8** runs whenever 5 agreed analyses are waiting, when no other company is pending, and always before F9.
5. **Pending check:** after every F8, run `python tools/scripts/check_pending.py`. When it prints `PENDING: 0` and at least one F8 ran this run, send back to F4 any gate reject whose market cap has fallen 20% or more since its gate check (compare with `triage.csv`); those that pass flow through F6-F8 like the rest. When nothing is left, run F9 once (decide, two rechecks, write).
6. **F9 finds a new holding** not on `company_list.csv` → add it, run it through F6-F8, then F9 again.

## Run rules
- **Pending results:** companies are analysed on their latest declared results. At run start, create the sheet tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1. F8 lists there the companies that haven't declared the run quarter. After the quarter's SEBI deadline, schedule a reminder to the user to re-run them.
- **Re-research:** a company is re-researched only when it has declared newer results than those used, or when the user asks; a quarter passing isn't a reason. An interrupted analysis is resumed from `status.csv`, not restarted. The sheet keeps a company's last row until its replacement completes.
- **New quarter:** each results season starts the new quarter's run: F1-F5 again (F5 reviews, not rebuilds, the previous sector map; `process/future/screens.json` is reviewed, not rebuilt), then companies flow as above, with F6 fetching only what is new.
- **Learnings:** after each F6, fold anything new in `process/fetch_learnings.md` into `f6_fetch.md` or `data_rules.md`; after each recheck, apply its learnings per `recheck.md`. Changes that can alter outcomes go in `acknowledgements.md` (`CLAUDE.md`, "Updates from learnings").

## Orchestrator duties
- **Claim the run:** one orchestrator per run. It writes at the top of `progress.md`: "Orchestrator: <session or thread>, since <time>, last update <time>", and refreshes the last-update time at every hand-off. Another session takes over only if the user asks, or the claim hasn't been updated for 2+ hours and that session is gone; it notes the takeover.
- **Brief each helper** with only its phase file (plus what that file names), the run folder, and its company or batch. Start the next phase yourself when a helper finishes.
- **Before every hand-off** update `status.csv` and `progress.md`, so a new orchestrator can resume exactly:
  - `status.csv` columns: `sym, phase, state, stage, loops_to_p6, results_used, updated, note`. `phase` is F4-F9; `state` is queued / running / done / blocked; `stage` is main / recheck1 / recheck2 for F7.
  - `progress.md`: the claim line, then a checklist: phases done, running (with model), next, open items for the user. Short lines, no prose paragraphs. The thread's to-do list mirrors it.

## Resuming
1. Read `CLAUDE.md`, this file, the run's `progress.md` and `status.csv`.
2. Take over the claim if allowed (above).
3. For each company or batch marked running: check its output files. A complete output means the phase finished: record it and move on. A partial one means the helper stopped: restart that phase for that company, telling the helper which files exist.
4. Continue from the first queued item in the order of work.
