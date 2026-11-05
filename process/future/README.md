# The process: map, order of work and resuming

Read by the orchestrator (any session that runs or resumes a run). Where each data item comes from, and what is already settled about each source: the top two sections of `tools/tools.md`. Helpers get only their own phase file plus what it names. Standing instructions and working preferences: `CLAUDE.md`.

## In one picture
```
F1 holdings ─┐
F2 screens ──┴─> F3 triage ─> F4 gate (+F4R) ─> F5 sector map (+F5R) ─> F6 company list
                                                                             │
             ┌───────────────────────────────────────────────────────────────┘  one company at a time, in list order
             v
            F7 fetch scripts ─> F8 fetch helper ──changed?──no──> done for this run
                                   │ yes
             ┌─────────────────────┘
             v
            F9 analysis ─> F9R1 ─> F9R2 ─> F10 listing (batched)
             ^ NEW_RESULTS (max 2 loops, back through F7)
                                      all companies done ─> F11 allocation (+F11R1, F11R2) ─> F12 sheet write
```

## Phases
screener.in (through the screener library in scripts: `scr_tool.py` for screens, `scr_company.py` for company data; `tools/tools.md`) is the main source, with NSE/BSE for the rest (`process/data_rules.md`). No phase needs Tapetide.

Every step has its own major number. A step that repeats is written X.0 here; its runs are X.1, X.2 … (never .0 for a real run): gate and listing batches in order, per-company steps by the company's position in `company_list.csv` (`F9.3` is the third company). A recheck takes the number of what it checks (F4R.2 checks F4.2; F9R1.3 and F9R2.3 are F9.3's first and second rechecks). Labels: `CLAUDE.md`, "Labels". Outputs are in `runs/future/<FYyyQn>/` unless noted.

| Step | Standard name | Model / effort or script | File | Inputs | Outputs | Done when |
|---|---|---|---|---|---|---|
| F1 | Holdings | orchestrator (`kite_holdings.py`) | `f1_holdings.md` | Kite, or the last saved holdings | run folder, `holdings.csv`, sheet's pending tab | holdings saved (or last ones kept, user told) |
| F2 | Screens | Sonnet low | `f2_screens.md` | `process/future/screens.json`, screener screens | `screens/`, `universe.csv` | every screen and band page saved, totals match |
| F3 | Triage | script (`triage.py`) | `f3_triage.md` | `universe.csv`, `holdings.csv` | `triage.csv`, `gate_batches.json` | every universe company and holding has a triage row |
| F4.0 | Gate | Opus medium, batches of ~10 | `f4_gate.md` | `gate_batches.json`, `triage.csv`, `scr/`, filings | `gate/bNN.json`, `gate/<SYM>.json` | every company in the batch has a decision |
| F4R.n | Gate recheck | Opus medium | `f4r_gate_recheck.md` | `gate/bNN.json`, `gate/<SYM>.json` | `gate/bNN_rc1.json` (rc2 if needed), `gate/decisions.csv` (`gate_merge.py`) | per `recheck.md` |
| F5 | Sector map | Opus medium | `f5_sector_map.md` | gate survivors and holdings, gate files, rule 21, official sources | `sector_map.md`, `sector_of.tsv` | every listed company has a sector and tier |
| F5R | Sector map recheck | Opus medium | `f5r_sector_recheck.md` | `sector_map.md`, `sector_of.tsv` | `sector_map_rc1.md` (rc2 if needed) | per `recheck.md` |
| F6 | Company list | orchestrator | `f6_company_list.md` | `holdings.csv`, `gate/decisions.csv`, `sector_of.tsv` | `company_list.csv` | every holding and gate survivor listed, in order |
| F7.0 | Fetch scripts | scripts (`scr_company.py`, `scr_docs.py`), one company | `f6_company_list.md` ("F7.0"), `f8_fetch.md` step 2 | `company_list.csv`, screener, exchange links | `data/companies/<SYM>/` (`scr/`, documents) | both scripts ran |
| F8.0 | Fetch helper | Sonnet medium, one company | `f8_fetch.md` | F7's files, filings | `data/companies/<SYM>/` (documents, `scr/`, `bse/`, `facts.json`, `index.json`) | reply `CHANGED: yes/no` |
| F9.0 | Deep analysis | Opus high, one company | `f9_analysis.md` | `process/investing_rules.md`, `sector_map.md`, gate file, `data/companies/<SYM>/` | `analysis/<SYM>/main.json`, `.md` | reply with buckets and EPS paths, or `NEW_RESULTS` |
| F9R1.n | Analysis recheck 1 | Opus medium (Opus high for an `unresolved` judgement call) | `f9r_analysis_recheck.md` | `analysis/<SYM>/main.json` | `analysis/<SYM>/recheck1.json`, `.md` | per `recheck.md` |
| F9R2.n | Analysis recheck 2 | Opus medium (Opus high for an `unresolved` judgement call) | `f9r_analysis_recheck.md` | `analysis/<SYM>/recheck1.json` | `analysis/<SYM>/recheck2.json`, `.md` | per `recheck.md` |
| F10.0 | Listing | Sonnet low, batches of agreed analyses | `f10_listing.md` | agreed analyses (`recheck2.json` or later) | Data, Data Flags, pending tabs; `runs/future/verdict_history.csv` | every agreed analysis since the last listing is in the sheet |
| F11 | Allocation | Opus medium | `f11_allocation.md` (part "decide") | Kite holdings, `company_list.csv`, bucket and Data tabs, rules | `holdings.csv`, `allocation/main.json` | decisions written with reasons |
| F11R | Allocation recheck | Opus medium, rechecks 1 and 2 (F11R1, F11R2) | `f11r_allocation_recheck.md` | `allocation/main.json`, then `recheck1.json`; `holdings.csv` | `allocation/recheck1.json`, `recheck2.json` | per `recheck.md` |
| F12 | Sheet write | Sonnet low | `f11_allocation.md` (part "write") | the last recheck's file, `holdings.csv` | Holdings and Allocation tabs | rows match the last recheck exactly |

Orchestrator: Sonnet medium (Opus medium when judging a recheck conflict or a rule change; Opus high only when clearly needed, saying why). Every to-do list names each phase's model and effort (e.g. "F9.3 (RELIANCE): Deep analysis [Opus high]").

## Order of work
1. **Run setup and F1.** A run is named after the latest quarter that has ended (`FYyyQn`), even if not every company has declared it. Create `runs/future/<FYyyQn>/`, set the run in `tools/scripts/config.py` (or the `RUN` environment variable), and do F1. Best started after the quarter's results deadline (45 days after quarter end; 60 for Q4), so most companies are fetched once.
2. **F2 → F3 → F4 (+F4R) per batch → F5 (+F5R) → F6.** F2 and F1 are independent. F4 batches run one after another. Before each batch, the orchestrator runs `uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM>` for every company in it. Each batch's recheck runs before the next batch, and its learnings are applied first.
3. **Companies flow one at a time** through F7 → F8 → F9 → F9R1 → F9R2, in `company_list.csv` order (holdings first), so each company's learnings reach the next. In F7 the orchestrator runs the fetch scripts named in `f8_fetch.md` step 2.
   - F8 replies `CHANGED: no` → that company is done for this run (status F10 done, note "no change").
   - F9 or a recheck replies `NEW_RESULTS` → back to F7 for that company alone, then restart F9. After 2 such loops, tell the user and tell F9 to carry on with the data it has.
   - After F9R2: copy `recheck2.md` to `analysis/<SYM>/<SYM>.md` (the agreed analysis); apply its learnings and any sector-note proposals (telling the user what changed) before the next company.
4. **F10** runs whenever 5 agreed analyses are waiting, when no other company is pending, and always before F11.
5. **Pending check:** after every F10, run `python tools/scripts/check_pending.py`. When it prints `PENDING: 0` and at least one F10 ran this run, send back to F4 any gate reject whose market cap has fallen 20% or more since its gate check (compare with `triage.csv`); those that pass flow through F7-F10 like the rest. When nothing is left, run F11 once (decide, two rechecks, write).
6. **F11 finds a new holding** not on `company_list.csv` → add it, run it through F7-F10, then F11 again.

## Run rules
- **Pending results:** companies are analysed on their latest declared results. At run start, create the sheet tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1. F10 lists there the companies that haven't declared the run quarter. After the quarter's SEBI deadline, schedule a reminder to the user to re-run them.
- **Re-research:** a company is re-researched only when it has declared newer results than those used, or when the user asks; a quarter passing isn't a reason. An interrupted analysis is resumed from `status.csv`, not restarted. The sheet keeps a company's last row until its replacement completes.
- **New quarter:** each results season starts the new quarter's run: F1-F5 again (F5 reviews, not rebuilds, the previous sector map; `process/future/screens.json` is reviewed, not rebuilt), then companies flow as above, with F7 and F8 fetching only what is new.
- **Learnings:** after each F8, fold anything new in `process/fetch_learnings.md` into `f8_fetch.md` or `data_rules.md`; after each recheck, apply its learnings per `recheck.md`. Tell the user about changes that alter an agreed outcome.

## Orchestrator duties
- **Claim the run:** one orchestrator per run. It writes at the top of `progress.md`: "Orchestrator: <session or thread>, since <time>, last update <time>", and refreshes the last-update time at every hand-off. Another session takes over only if the user asks, or the claim hasn't been updated for 2+ hours and that session is gone; it notes the takeover.
- **Brief each helper** with only its phase file (plus what that file names), the run folder, and its company or batch. Start the next phase yourself when a helper finishes.
- **Before every hand-off** update `status.csv` and `progress.md`, so a new orchestrator can resume exactly:
  - `status.csv` columns: `sym, phase, state, stage, loops_to_f7, results_used, updated, note`. `phase` is F4-F12; `state` is queued / running / done / blocked; `stage` is main / recheck1 / recheck2 for F9.
  - `progress.md`: the claim line, then a checklist: phases done, running (with model), next, open items for the user. Short lines, no prose paragraphs. The thread's to-do list mirrors it.

## Resuming
1. Read `CLAUDE.md`, this file, the run's `progress.md` and `status.csv`.
2. Take over the claim if allowed (above).
3. For each company or batch marked running: check its output files. A complete output means the phase finished: record it and move on. A partial one means the helper stopped: restart that phase for that company, telling the helper which files exist.
4. Continue from the first queued item in the order of work.
