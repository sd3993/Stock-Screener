# The process: map, order of work and resuming

Read by the orchestrator (any session that runs or resumes a run). Helpers get only their own phase file plus what it names. Standing instructions and working preferences: `CLAUDE.md`.

## In one picture
```
P1 holdings ─┐
P2 screens ──┴─> P3 triage ─> P4 gate (+P4R) ─> P5 sector map & company list (+P5R)
                                                   │
             ┌─────────────────────────────────────┘  one company at a time, in list order
             v
            P6 fetch ──changed?──no──> done for this run
             │ yes
             v
            P7 analysis ─> P7R1 ─> P7R2 ─> P8 sheet listing (batched)
             ^ NEW_RESULTS (max 2 loops)
                                      all companies done ─> P9 allocation (+P9R1, P9R2) ─> P9W sheet write
```

## Phases
Tapetide calls are per company unless noted. They are estimates until the first run's call log (`tools/tools.md`, "Tapetide") replaces them.

| # | Phase | Who | Model / effort | File | Output (in `runs/<FYyyQn>/` unless noted) | Done when | Tapetide calls |
|---|---|---|---|---|---|---|---|
| P1 | Holdings from Kite; run setup | orchestrator | (orchestrator's) | `p1_holdings.md` | `holdings.csv`, sheet's pending tab | holdings saved (or last ones kept, user told) | 0 |
| P2 | Market screens and field dumps | script; helper only without a token | Sonnet low | `p2_screens.md` | `screens/`, `universe.csv` | every screen and dump page saved, totals match | ~400 for the whole market, once a quarter |
| P3 | Number triage and gate batches | script | none | `p3_triage.md` | `triage.csv`, `gate_batches.json` | every universe company and holding has a triage row | 0 |
| P4 | Gate, one batch of ~10 | helper | Opus medium | `p4_gate.md` | `gate/bNN.json`, `gate/<SYM>.json` | every company in the batch has a decision | ~4-6 |
| P4R | Gate recheck | helper | Opus medium | `p4r_gate_recheck.md` | `gate/bNN_rc1.json` (rc2 if needed) | per `recheck.md` | 0-3 |
| P5 | Sector map and company list | helper (map), orchestrator (list) | Opus medium | `p5_sector_map.md` | `sector_map.md`, `sector_of.tsv`, `company_list.csv` | every listed company has a sector and tier | ~1 (profile, if not cached) |
| P5R | Sector map recheck | helper | Opus medium | `p5r_sector_recheck.md` | `sector_map_rc1.md` (rc2 if needed) | per `recheck.md` | 0 |
| P6 | Fetch one company | script + helper | Sonnet medium | `p6_fetch.md` | `data/companies/<SYM>/` (documents, `api/`, `facts.json`) | reply `CHANGED: yes/no` | ~15 first time; ~5 on a repeat |
| P7 | Deep analysis, one company | helper | Opus high | `p7_analysis.md` | `analysis/<SYM>/main.json`, `.md` | reply with buckets and EPS paths, or `NEW_RESULTS` | 0-3 |
| P7R | Analysis rechecks 1 and 2 | helper each | Opus medium (Opus high for an `unresolved` judgement call) | `p7r_analysis_recheck.md` | `analysis/<SYM>/recheck1.json`, `recheck2.json` (+ `.md`) | per `recheck.md` | 0-3 each |
| P8 | Sheet listing, batch of agreed analyses | helper | Sonnet low | `p8_listing.md` | Data, Data Flags, pending tabs; `runs/verdict_history.csv` | every agreed analysis since the last listing is in the sheet | 1 per 20 companies (prices) |
| P9 | Allocation and holdings decision | helper | Opus medium | `p9_allocation.md` | `allocation/main.json` | decisions written with reasons | 0 |
| P9R | Allocation rechecks 1 and 2 | helper each | Opus medium | `p9r_allocation_recheck.md` | `allocation/recheck1.json`, `recheck2.json` | per `recheck.md` | 0 |
| P9W | Sheet write of the allocation | helper | Sonnet low | `p9_allocation.md` (part "write") | Holdings and Allocation tabs | rows match the last recheck exactly | 0 |

Orchestrator: Sonnet medium (Opus medium when judging a recheck conflict or a rule change; Opus high only when clearly needed, saying why). Every to-do list names each phase's model and effort (e.g. "P7 [Opus high]").

## Order of work
1. **Run setup and P1.** A run is named after the latest quarter that has ended (`FYyyQn`), even if not every company has declared it. Create `runs/<FYyyQn>/`, set the run in `tools/scripts/config.py` (or the `RUN` environment variable), and do P1. Best started after the quarter's results deadline (45 days after quarter end; 60 for Q4), so most companies are fetched once.
2. **P2 → P3 → P4 (+P4R) per batch → P5 (+P5R).** P2 and P1 are independent. P4 batches run one after another; each batch's recheck runs before the next batch, and its learnings are applied first.
3. **Companies flow one at a time** through P6 → P7 → P7R1 → P7R2, in `company_list.csv` order (holdings first), so each company's learnings reach the next.
   - P6 replies `CHANGED: no` → that company is done for this run (status P8 done, note "no change").
   - P7 or a recheck replies `NEW_RESULTS` → back to P6 for that company alone, then restart P7. After 2 such loops, flag it (`acknowledgements.md`) and tell P7 to carry on with the data it has.
   - After P7R2: copy `recheck2.md` to `analysis/<SYM>/<SYM>.md` (the agreed analysis); apply its learnings and any sector-note proposals (listed for acknowledgement) before the next company.
4. **P8** runs whenever 5 agreed analyses are waiting, when no other company is pending, and always before P9.
5. **Pending check:** after every P8, run `python tools/scripts/check_pending.py`. When it prints `PENDING: 0` and at least one P8 ran this run, send back to P4 any gate reject whose market cap has fallen 20% or more since its gate check (compare with `triage.csv`); those that pass flow through P6-P8 like the rest. When nothing is left, run P9 once (decide, two rechecks, write).
6. **P9 finds a new holding** not on `company_list.csv` → add it, run it through P6-P8, then P9 again.

## Run rules
- **Pending results:** companies are analysed on their latest declared results. At run start, create the sheet tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1. P8 lists there the companies that haven't declared the run quarter. After the quarter's SEBI deadline, schedule a reminder to the user to re-run them.
- **Re-research:** a company is re-researched only when it has declared newer results than those used, or when the user asks; a quarter passing isn't a reason. An interrupted analysis is resumed from `status.csv`, not restarted. The sheet keeps a company's last row until its replacement completes.
- **New quarter:** each results season starts the new quarter's run: P1-P5 again (P5 reviews, not rebuilds, the previous sector map; `process/screens.json` is reviewed, not rebuilt), then companies flow as above, with P6 fetching only what is new.
- **Learnings:** after each P6, fold anything new in `process/fetch_learnings.md` into `p6_fetch.md` or `data_rules.md`; after each recheck, apply its learnings per `recheck.md`. List every such change in `acknowledgements.md`.

## Orchestrator duties
- **Claim the run:** one orchestrator per run. It writes at the top of `progress.md`: "Orchestrator: <session or thread>, since <time>, last update <time>", and refreshes the last-update time at every hand-off. Another session takes over only if the user asks, or the claim hasn't been updated for 2+ hours and that session is gone; it notes the takeover.
- **Brief each helper** with only its phase file (plus what that file names), the run folder, and its company or batch. Start the next phase yourself when a helper finishes.
- **Before every hand-off** update `status.csv` and `progress.md`, so a new orchestrator can resume exactly:
  - `status.csv` columns: `sym, phase, state, stage, loops_to_p6, results_used, updated, note`. `phase` is P4-P9; `state` is queued / running / done / blocked; `stage` is main / recheck1 / recheck2 for P7.
  - `progress.md`: the claim line, then a checklist: phases done, running (with model), next, open items for the user. Short lines, no prose paragraphs. The thread's to-do list mirrors it.
- **Tapetide quota:** before a phase that calls Tapetide, check the remaining quota (`python tools/scripts/tt.py usage`, or the call log when there's no token). If the phase can't finish today, do what fits and carry on with other work; never leave one company half-fetched.

## Resuming
1. Read `CLAUDE.md`, this file, the run's `progress.md` and `status.csv`.
2. Take over the claim if allowed (above).
3. For each company or batch marked running: check its output files. A complete output means the phase finished: record it and move on. A partial one means the helper stopped: restart that phase for that company, telling the helper which files exist.
4. Continue from the first queued item in the order of work.
