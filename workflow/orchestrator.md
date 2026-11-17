# Orchestrator manual: running a run (map, order of work, run rules, resuming)

Read by the orchestrator (any session that runs or resumes a run). The modes, the rules every step follows, the step table and the state folders: `/workflow/WORKFLOW.md`.

## In one picture
```
full:
S1 setup+holdings ─┐
S2 screens ────────┴─> S3 triage ─> S4 sector numbers ─> S5 sector map (+S5R) ─> S6 gate, tailwind sectors first (+S6R)
                                                                                    │
recheck:                                                                            v
S1 setup+holdings ─> S4 stage ─> S5 (marker review) ────────────────────────────> S7 company list
                                                                                    │ one company at a time, in list order
                                                                                    v
                                 S8 fetch scripts ─> S9 marker check (recheck mode only) ──hold──> S12 (history row only)
                                                            │ full mode, or verify / re-analyse
                                                            v
                                 S10 fetch subagent ──CHANGED: no (full mode)──> done for this run
                                                            │
                                                            v
                                 S11 analysis ─> S11R1 ─> S11R2 ─> S12 listing (batched; thesis register)
                                   ^ NEW_RESULTS (max 2 loops, back through S8)
                                                            all companies done ─> S13 allocation (+S13R1, S13R2) ─> S14 sheet write
```

## Step inputs, outputs and completion

| Step | Inputs | Outputs | Done when |
|---|---|---|---|
| S1 | Kite, or the last saved holdings | run folder, `progress.md` (mode), `status.csv`, `holdings.csv`, sheet's pending tab | holdings saved (or last ones kept, user told) |
| S2 | `/workflow/screens.json`, screener screens | `screens/`, `universe.csv` | the script ends with exit 0: every screen and band page saved, totals match |
| S3 | `universe.csv`, `holdings.csv` | `triage.csv`, `gate_batches.json` | every universe company and holding has a triage row |
| S4 | `universe.csv`, `triage.csv`, `holdings.csv`, `scr/overview.json`, `scr/history.json`, `scr/shareholding.json`, `scr/announcements.json` | `sector_clusters.csv`, `sector_stage.csv` | every queued company and holding has an industry label or a recorded gap; every industry with 5+ companies has its stage numbers |
| S5 | S4's files, the previous `sector_map.md`, `sectors.json`, `sector_calls_score.md` (`sectors.py score`), the sector preferences rule, official sources | `sector_map.md`, `sectors.json`, `sector_of.tsv`, reordered `gate_batches.json`, rows in `runs/sector_calls.csv` | every sector entry complete (every item `/principles/sector_rules.md` requires), every queued company and holding has a sector and rank, every call logged |
| S5R | `sector_map.md`, `sectors.json` | `sector_map_rc1.md`, `sectors_rc1.json` (rc2 if needed) | per `/principles/recheck_rules.md` |
| S6.0 | `gate_batches.json`, `triage.csv`, `sector_map.md`, `scr/`, filings | `gate/bNN.json`, `gate/<SYM>.json` | every company in the batch has a decision and a confirmed sector |
| S6R.n | `gate/bNN.json`, `gate/<SYM>.json` | `gate/bNN_rc1.json` (rc2 if needed), `gate/decisions.csv` (`gate_merge.py`) | per `/principles/recheck_rules.md` |
| S7 | `holdings.csv`; full: `gate/decisions.csv`, `sector_of.tsv`; recheck: `runs/companies/*/thesis.json`, the sheet's Data tab when readable | `company_list.csv`, `status.csv` rows | every holding and survivor (or company with a thesis) listed, in order |
| S8.0 | `company_list.csv`, screener, exchange links | `data/companies/<SYM>/` (`scr/`, documents) | both scripts ran |
| S9.0 | `runs/companies/<SYM>/thesis.json`, `sectors.json` marker states, `data/companies/<SYM>/scr/`, `facts.json` | `marker_check.csv` rows with an action; the company's `marker_checks.csv` history | the company has an action: hold / verify / re-analyse / integrity review |
| S10.0 | S8's files, filings | `data/companies/<SYM>/` (documents, `scr/`, `bse/`, `facts.json`, `index.json`) | reply `CHANGED: yes/no` |
| S11.0 | `/principles/investing_rules.md`, `sector_map.md`, gate file, `data/companies/<SYM>/` | `runs/companies/<SYM>/<FYyyQn>/main.json`, `.md` | reply with status, visible-until date, markers and EPS paths, or `NEW_RESULTS` |
| S11R1.n | `<SYM>/<FYyyQn>/main.json` | `<SYM>/<FYyyQn>/recheck1.json`, `.md` | per `/principles/recheck_rules.md` |
| S11R2.n | `<SYM>/<FYyyQn>/recheck1.json` | `<SYM>/<FYyyQn>/recheck2.json`, `.md` | per `/principles/recheck_rules.md` |
| S12.0 | agreed analyses (the highest `recheck<N>.json`); recheck: S9 holds | Data, Data Flags, pending tabs; `runs/verdict_history.csv`; `runs/companies/<SYM>/thesis.json` | every agreed analysis (and every marker-check hold) since the last listing is recorded and read back |
| S13 | Kite holdings, `company_list.csv`, List, Watchlist and Data tabs, `runs/companies/<SYM>/thesis.json`, rules | `holdings.csv`, `allocation/main.json` | decisions written with reasons |
| S13R | `allocation/main.json`, then `recheck1.json`; `holdings.csv` | `allocation/recheck1.json`, `recheck2.json` | per `/principles/recheck_rules.md` |
| S14 | the last recheck's file, `holdings.csv` | Holdings and Allocation tabs, Data top-up columns | rows match the last recheck exactly (read back) |

## Order of work
### full
1. **Setup and S1.** Create `runs/<FYyyQn>/` with mode `full` (`s1_setup.md`). Best started after the quarter's results deadline (45 days after quarter end; 60 for Q4), so most companies are fetched once.
2. **S2 → S3 → S4 → S5 (+S5R).** S1 and S2 are independent. After S5R, run `sectors.py order` (reorders the gate batches, tailwind sectors first, and queues the emerging entries' companies) and `sectors.py log`.
3. **S6 (+S6R) per batch**, in the order `sectors.py order` wrote. Before each batch the orchestrator runs `uvx --from screener-mcp==0.5.0 python scripts/scr_company.py <SYM>` for every company in it. Each batch's recheck runs before the next batch, and its learnings are applied first. After the last batch, `gate_merge.py`, then `sectors.py order --from-gate` (sectors confirmed by the gate).
4. **S7**, then companies flow one at a time through S8 → S10 → S11 → S11R1 → S11R2, in `company_list.csv` order (holdings first, then by the gate's estimated CAGR), so each company's learnings reach the next.
   - S10 replies `CHANGED: no` → that company is done for this run (status S12 done, note "no change"), unless its thesis has no markers yet (then it goes on to S11).
   - S11 or a recheck replies `NEW_RESULTS` → back to S8 for that company alone, then restart S11. After 2 such loops, tell the user and tell S11 to carry on with the data it has.
   - After S11R2: copy the last recheck's `.md` to `<SYM>.md` in the same `runs/companies/<SYM>/<FYyyQn>/` folder (the agreed analysis); apply its learnings before the next company, and pass any sector-note proposal to the user (applied only on the user's OK).
5. **S12** runs whenever 5 agreed analyses are waiting, when no other company is pending, and always before S13.
6. **Pending check:** after every S12, run `python -I scripts/run.py pending`. When it prints `PENDING: 0` and at least one S12 ran this run, send back to S6 any gate reject the re-gating standard lets back in (`/principles/filter_rules.md`; its price now against the one in `triage.csv`); those that pass flow through S8-S12 like the rest. When nothing is left, run S13 once (decide, two rechecks, write).
7. **S13 finds a new holding** not on `company_list.csv` → add it, run it through S8-S12, then S13 again.

### recheck
1. **Setup and S1** with mode `recheck`; copy the last full run's `sector_map.md`, `sectors.json` and `sector_of.tsv` into the run folder (`s1_setup.md`).
2. **S4 stage numbers** (`sectors.py stage --stage-only`, after refreshing the members' overviews; the recheck-mode part of `/workflow/s4_sector_numbers.md`) and **S5 in review mode**: only sector markers that are due, or whose machine-checked state changed, are reviewed; a sector marker that breaks marks every company in that sector for re-analysis and triggers a `full` run for that sector's map entry (tell the user).
3. **S7** (holdings plus every listed and watchlist name), then one company at a time: S8 → S9.
   - S9 action `hold` → S12 records a verdict-history row ("markers held, results FYyyQn"); nothing else changes.
   - `verify` (a marker near its line, or a figure the script couldn't read) → S10, then S9 again on the verified figures.
   - `re-analyse` (a marker broken, the half-yearly full re-analysis due, a watch whose awaited evidence is due, a new holding with no thesis, or the user asks) → S10 → S11 → S11R1 → S11R2 → S12, as in full mode.
   - `integrity review` (a governance filing matched an integrity term) → S10 → S11 at once (the analysis reads the filing first); a confirmed integrity flag overrides every marker (the integrity flags rule) and the user is told straight away.
4. **S13 → S13R → S14** as in full mode.

## Run rules
- **Sources:** before a step uses Kite or fetches from screener.in: `/sources/kite.md`, `/sources/screener.md`.
- **Pending results:** companies are analysed on their latest declared results. At run start, create the sheet tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1. S12 lists there the companies that haven't declared the run quarter. After the quarter's SEBI deadline, schedule a reminder to the user to re-run them.
- **Re-research:** a company is re-analysed only when S9 sends it (marker broken, integrity review, a watch's awaited evidence due, half-yearly re-analysis due: two newer quarters declared since the results its thesis used), when it has declared newer results in a full run, or when the user asks; a quarter passing isn't a reason by itself. An interrupted analysis is resumed from `status.csv`, not restarted. The sheet keeps a company's last row until its replacement completes.
- **Thesis markers:** every analysed company's markers (the exit rules and `/principles/sector_rules.md`) are in `runs/companies/<SYM>/thesis.json`, written by `thesis.py register` from the agreed analysis (S12); every S9 check is kept in the company's `marker_checks.csv`. How a break is weighed against the position: `/principles/investing_rules.md` (exit rules).
- **Sector calls:** every sector entry S5 writes or changes is logged in `runs/sector_calls.csv` with its date, stage and markers (`sectors.py log`); each run's S5 records marker states, and `sectors.py score` reports the hit rate of past calls (markers held or broken by their dates; the sector's later median return against the market). The hit rate is reported to the user with every full run's map.
- **New full run:** S2-S5 again (S5 reviews, not rebuilds, the last map; `/workflow/screens.json` is reviewed, not rebuilt), then companies flow as above, with S8 and S10 fetching only what is new.
- **Learnings:** after each S10, fold anything new in `/workflow/fetch_learnings.md` into `s10_fetch.md` or `/principles/data_rules.md`; after each recheck, apply its learnings per `/workflow/recheck.md`. Tell the user about changes that alter an agreed outcome.
- **Exit calls:** an S11 exit and an S13 Full exit go to the user at once, each with its urgency and the dated event behind it (the exit rules); the user picks the time.
- **Rules wording:** a change to `/principles/investing_rules.md` needs no process edit unless an output field changes.

## Orchestrator duties
Every to-do list names each step's tier (e.g. "S11.3 (RELIANCE): Deep analysis [deepest]"). Of the steps, the orchestrator itself only starts the scripts; every other step goes to a subagent (the global orchestrator boundary and concurrency limits: `~/.common-ai/COMMON_AI.md`).

- **Claim the run:** one orchestrator per run. It writes at the top of `progress.md`: "Orchestrator: <session or thread>, since <time>, last update <time>", and refreshes the last-update time at every hand-off. Another session takes over only if the user asks, or the claim hasn't been updated for 2+ hours and that session is gone; it notes the takeover.
- **Brief each subagent** (global subagent prompt brevity) with its step file, the run folder, the mode, and its company, batch or sector. When a subagent finishes, start the next step's script or subagent.
- **Before every hand-off** update `status.csv` and `progress.md`, so a new orchestrator can resume exactly:
  - `status.csv` columns: `sym, phase, state, stage, loops_to_s8, results_used, updated, note`. `phase` is S6-S14; `state` is queued / running / done / blocked; `stage` is main / recheck1 / recheck2 for S11, or the S9 action.
  - `progress.md`: the mode line and the claim line, then a checklist: steps done, running (with tier), next, open items for the user. Short lines, no prose paragraphs. The thread's to-do list mirrors it.
- **Flow:** S10-S11 companies flow one at a time, in `company_list.csv` order, so each one's learnings reach the next; gate batches likewise run one after another.
- **Labels:** every subagent, background task and watchdog, and every report about one: `<step> (<batch size or single company symbol>): <standard step name>`, e.g. `S6.3 (10): Gate`, `S11.3 (RELIANCE): Deep analysis`; a step that doesn't repeat has no bracket (`S3: Triage`). Numbers and standard names: the step table in `/workflow/WORKFLOW.md`.

## Resuming
1. Read `/COMMON_AI.md` (and the agent-specific file), `/workflow/WORKFLOW.md`, this file, the run's `progress.md` (mode first) and `status.csv`.
2. Take over the claim if allowed (above).
3. For each company, batch or sector marked running: check its output files. A complete output means the step finished: record it and move on. A partial one means the subagent stopped: restart that step for that item, telling the subagent which files exist. Scripts skip finished work (saved histories, statements, pages), so re-run their command.
4. Continue from the first queued item in the order of work for the run's mode.
