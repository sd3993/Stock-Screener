# The workflow: discovering future multibaggers (map, modes, order of work, resuming)

Read by the orchestrator (any session that runs or resumes a run). Where each data item comes from and what is settled about each source: the top two sections of `tools/tools.md`. Helpers get only their own step file plus what it names. Standing instructions and working preferences: `COMMON_AI.md` (and the agent-specific file beside it). Investing rules: `process/investing_rules.md` (step files point to it and never restate it).

## Two modes, one pipeline
- **`full`:** research from scratch: market-wide screens, sector tailwind map, gate, then every holding and survivor analysed. Run yearly, and at once when a sector marker breaks, a major policy is notified that touches a sector on the map or a preferred sector (rule 21), or the list runs thin (fewer names passing the hurdle than rule 13's position count needs).
- **`recheck`:** existing companies only (holdings and every name currently listed in the sheet), each quarter after results. It is the same pipeline entered at the company list (S9) with the last full run's sector map; same step files, same status files. A script checks each company's thesis markers (S11); only companies it sends on get the fetch helper and a new analysis.

Screening is always market-wide (S2, S3), never sector-only. Why (evidence from the playbook base data, `data/playbook/sector_test.md`): multibaggers cluster by industry only moderately (the top-20% industries held 47% of 3x-in-5-years winners against 38% by chance); a company with high EPS growth in a low-growth industry still reached 3x 48% of the time against 56% in a high-growth one; and no backward-looking industry figure predicted which industries would produce winners (rank correlation about 0 from 2016). So the sector map orders and frames the work (which companies go first, each company's thesis horizon and re-rating case, which sectors get a playbook); it never excludes a company. Because backward numbers didn't predict, every sector call is logged with its date and markers, and its hit rate is tracked across runs (S5).

## In one picture
```
full:
S1 setup+holdings ─┐
S2 screens ────────┴─> S3 triage ─> S4 sector numbers ─> S5 sector map (+S5R) ─┬─> S6 playbook data ─> S7 playbook (+S7R)   (chosen sectors only)
                                                                               └─> S8 gate, tailwind sectors first (+S8R)
                                                                                        │
recheck:                                                                                v
S1 setup+holdings ─> S4 stage ─> S5 (marker review) ─────────────────────────────> S9 company list
                                                                                        │ one company at a time, in list order
                                                                                        v
                                     S10 fetch scripts ─> S11 marker check (recheck mode only) ──hold──> S14 (history row only)
                                                                │ full mode, or verify / re-analyse
                                                                v
                                     S12 fetch helper ──CHANGED: no (full mode)──> done for this run
                                                                │
                                                                v
                                     S13 analysis ─> S13R1 ─> S13R2 ─> S14 listing (batched; thesis register)
                                       ^ NEW_RESULTS (max 2 loops, back through S10)
                                                                all companies done ─> S15 allocation (+S15R1, S15R2) ─> S16 sheet write
```

## Steps
screener.in (through the screener library in scripts: `scr_tool.py` for screens, `scr_company.py` for company data; `tools/tools.md`) is the main source, with NSE/BSE for the rest (`process/data_rules.md`). No step needs Tapetide.

Every step has its own major number. A step that repeats is written X.0 here; its runs are X.1, X.2 … (never .0 for a real run): batches in order, per-company steps by the company's position in `company_list.csv` (`S13.3` is the third company), playbooks by the sector's position in `sectors.json`. A recheck takes the number of what it checks (S8R.2 checks S8.2; S13R1.3 and S13R2.3 are S13.3's first and second rechecks). Labels: `COMMON_AI.md`, "Helpers in this project" ("Labels"). Outputs are in the run folder `runs/<FYyyQn>/` unless noted. "(to write)" marks a script specified in `runs/new_scripts_spec.md` and not written yet; until it exists, a light-tier helper does that part from the same spec (standard tier if the light trial fails).

Tiers (script / light / standard / deep / deepest) are defined in the user's global common instruction file ("Capability tiers"); the lightest tier that is accurate, deepest only where noted with the reason.

| Step | Standard name | Mode(s) | Tier or script | File | Inputs | Outputs | Done when |
|---|---|---|---|---|---|---|---|
| S1 | Setup and holdings | full, recheck | scripts `run_setup.py` (to write), `kite_holdings.py` | `s1_setup.md` | Kite, or the last saved holdings | run folder, `progress.md` (mode), `status.csv`, `holdings.csv`, sheet's pending tab | holdings saved (or last ones kept, user told) |
| S2 | Screens | full | light (trial: accept only if `build_universe.py`'s checks pass on the first run; else standard); `run_screens.py` (to write) replaces it | `s2_screens.md` | `process/screens.json`, screener screens | `screens/`, `universe.csv` | every screen and band page saved, totals match |
| S3 | Triage | full | script `triage.py` | `s3_triage.md` | `universe.csv`, `holdings.csv` | `triage.csv`, `gate_batches.json` | every universe company and holding has a triage row |
| S4 | Sector numbers | full; recheck (stage numbers only) | scripts `scr_company.py --only overview,shareholding`, `sector_numbers.py` (to write) | `s4_sector_numbers.md` | `triage.csv`, `holdings.csv`, `scr/overview.json`, `scr/history.json`, `scr/shareholding.json`, `scr/announcements.json` | `sector_clusters.csv`, `sector_stage.csv` | every queued company and holding has an industry label or a recorded gap; every industry with 5+ companies has its stage numbers |
| S5 | Sector tailwind map | full (build or review); recheck (review due sector markers only) | deep; then scripts `sector_order.py` (to write), `sector_calls.py` (to write) | `s5_sector_map.md` | S4's files, the previous `sector_map.md`, `sectors.json`, `runs/sector_calls.csv`, rule 21, official sources | `sector_map.md`, `sectors.json`, `sector_of.tsv`, reordered `gate_batches.json`, rows in `runs/sector_calls.csv` | every sector entry complete (all fields in the step file), every queued company and holding has a sector and rank, every call logged |
| S5R | Sector map recheck | full; recheck when a marker status changed | deep | `s5r_sector_recheck.md` | `sector_map.md`, `sectors.json` | `sector_map_rc1.md`, `sectors_rc1.json` (rc2 if needed) | per `recheck.md` |
| S6.0 | Playbook data | full, chosen sectors | scripts `mb_history.py`, `mb_outcomes.py`, `mb_features.py`, `mb_sector_test.py`, `playbook_data.py` (to write) | `s6_playbook.md` ("S6") | `sectors.json`, `data/playbook/` | `runs/playbooks/<sector>/episodes.csv`, `data.md` | the sector's episodes and their companies listed with outcomes and start features |
| S7.0 | Sector playbook | full, chosen sectors | deepest, one sector: it writes the sector notes every later analysis in that sector applies, weighing past episodes read strictly without hindsight; a few a year | `s6_playbook.md` ("S7") | S6's files, the companies' dated filings, `data/playbook/experts.md`, `process/investing_rules.md` | `runs/playbooks/<sector>/playbook.md`, `notes_proposed.md` | every episode studied, every proposed note has passed the tests or is marked "possibly chance" |
| S7R.n | Playbook recheck | full | deep | `s6_playbook.md` ("S7R") | `playbook.md`, cited documents | `playbook_rc1.md` | per `recheck.md` |
| S8.0 | Gate | full | deep, batches of ~10, tailwind sectors first | `s8_gate.md` | `gate_batches.json`, `triage.csv`, `sector_map.md`, `scr/`, filings | `gate/bNN.json`, `gate/<SYM>.json` | every company in the batch has a decision and a confirmed sector |
| S8R.n | Gate recheck | full | deep | `s8r_gate_recheck.md` | `gate/bNN.json`, `gate/<SYM>.json` | `gate/bNN_rc1.json` (rc2 if needed), `gate/decisions.csv` (`gate_merge.py`) | per `recheck.md` |
| S9 | Company list | full, recheck | script `company_list.py` (to write) | `s9_company_list.md` ("S9") | `holdings.csv`; full: `gate/decisions.csv`, `sector_of.tsv`; recheck: sheet's Data tab tickers, `runs/theses/` | `company_list.csv`, `status.csv` rows | every holding and survivor (or listed name) listed, in order |
| S10.0 | Fetch scripts | full, recheck | scripts `scr_company.py`, `scr_docs.py`, one company | `s9_company_list.md` ("S10.0"), `s12_fetch.md` step 2 | `company_list.csv`, screener, exchange links | `data/companies/<SYM>/` (`scr/`, documents) | both scripts ran |
| S11.0 | Marker check | recheck | script `marker_check.py` (to write), one company | `s11_marker_check.md` | `runs/theses/<SYM>.json`, `sectors.json` marker states, `data/companies/<SYM>/scr/`, `facts.json` | `marker_check.csv` row with an action | the company has an action: hold / verify / re-analyse / integrity review |
| S12.0 | Fetch helper | full; recheck (verify and re-analyse only) | standard, one company: exact figure extraction from filings (OCR-garbled scans, restated columns) decides verdicts, so not light until a light-tier trial on one company matches a standard-tier run figure for figure | `s12_fetch.md` | S10's files, filings | `data/companies/<SYM>/` (documents, `scr/`, `bse/`, `facts.json`, `index.json`) | reply `CHANGED: yes/no` |
| S13.0 | Deep analysis | full; recheck (re-analyse only) | deepest, one company: the verdict the user trades on, weighing many conflicting filings, guidance records and the sector case; two rechecks follow | `s13_analysis.md` | `process/investing_rules.md`, `sector_map.md`, playbook, gate file, `data/companies/<SYM>/` | `analysis/<SYM>/main.json`, `.md` | reply with horizon, markers and EPS paths, or `NEW_RESULTS` |
| S13R1.n | Analysis recheck 1 | full, recheck | deep (deepest for an `unresolved` judgement call) | `s13r_analysis_recheck.md` | `analysis/<SYM>/main.json` | `analysis/<SYM>/recheck1.json`, `.md` | per `recheck.md` |
| S13R2.n | Analysis recheck 2 | full, recheck | deep (deepest for an `unresolved` judgement call) | `s13r_analysis_recheck.md` | `analysis/<SYM>/recheck1.json` | `analysis/<SYM>/recheck2.json`, `.md` | per `recheck.md` |
| S14.0 | Listing | full, recheck | light, batches of agreed analyses (trial: the first batch read back cell by cell; else standard); script `thesis_register.py` (to write); `sheet_write.py listing` (to write) replaces the helper | `s14_listing.md` | agreed analyses (`recheck2.json` or later); recheck: `marker_check.csv` | Data, Data Flags, pending tabs; `runs/verdict_history.csv`; `runs/theses/<SYM>.json` | every agreed analysis (and every marker-check hold) since the last listing is recorded |
| S15 | Allocation | full, recheck | deep | `s15_allocation.md` (part "decide") | Kite holdings, `company_list.csv`, horizon and Data tabs, `runs/theses/`, rules | `holdings.csv`, `allocation/main.json` | decisions written with reasons |
| S15R | Allocation recheck | full, recheck | deep, rechecks 1 and 2 (S15R1, S15R2) | `s15r_allocation_recheck.md` | `allocation/main.json`, then `recheck1.json`; `holdings.csv` | `allocation/recheck1.json`, `recheck2.json` | per `recheck.md` |
| S16 | Sheet write | full, recheck | light (trial: read-back matches; else standard); `sheet_write.py allocation` (to write) replaces it | `s15_allocation.md` (part "write") | the last recheck's file, `holdings.csv` | Holdings and Allocation tabs | rows match the last recheck exactly |

Every to-do list names each step's tier (e.g. "S13.3 (RELIANCE): Deep analysis [deepest]"). No step is the orchestrator's: it starts the scripts, dispatches the helpers, tracks status and talks to the user, and its own tier is not part of the workflow (the user's global common instruction file: "Orchestrator", "Helper parallelism").

## Order of work
### full
1. **Setup and S1.** Create `runs/<FYyyQn>/` with mode `full` (`s1_setup.md`). Best started after the quarter's results deadline (45 days after quarter end; 60 for Q4), so most companies are fetched once.
2. **S2 → S3 → S4 → S5 (+S5R).** S1 and S2 are independent. After S5R, run `sector_order.py` (reorders the gate batches, tailwind sectors first) and `sector_calls.py log`.
3. **Playbooks (S6 → S7 → S7R), only for the sectors S5 chose** (where screen survivors cluster or forward evidence is strong, and no current playbook exists: one is current for 12 months, or until one of its sector's markers breaks). A deepest-tier helper runs alone, so playbooks run before the gate or between gate batches, never beside one. The orchestrator applies each playbook's agreed sector notes to `process/investing_rules.md` (telling the user what changed) before that sector's companies reach S13; general-rule proposals go to the user.
4. **S8 (+S8R) per batch**, in the order `sector_order.py` wrote. Before each batch the orchestrator runs `uvx --from screener-mcp==0.5.0 python tools/scripts/scr_company.py <SYM>` for every company in it. Each batch's recheck runs before the next batch, and its learnings are applied first. After the last batch, `gate_merge.py`, then `sector_order.py --from-gate` (sectors confirmed by the gate).
5. **S9**, then companies flow one at a time through S10 → S12 → S13 → S13R1 → S13R2, in `company_list.csv` order (holdings first, then by sector rank), so each company's learnings reach the next.
   - S12 replies `CHANGED: no` → that company is done for this run (status S14 done, note "no change"), unless its thesis has no markers yet (then it goes on to S13).
   - S13 or a recheck replies `NEW_RESULTS` → back to S10 for that company alone, then restart S13. After 2 such loops, tell the user and tell S13 to carry on with the data it has.
   - After S13R2: copy `recheck2.md` to `analysis/<SYM>/<SYM>.md` (the agreed analysis); apply its learnings and any sector-note proposals (telling the user what changed) before the next company.
6. **S14** runs whenever 5 agreed analyses are waiting, when no other company is pending, and always before S15.
7. **Pending check:** after every S14, run `python tools/scripts/check_pending.py`. When it prints `PENDING: 0` and at least one S14 ran this run, send back to S8 any gate reject whose market cap has fallen 20% or more since its gate check (compare with `triage.csv`); those that pass flow through S10-S14 like the rest. When nothing is left, run S15 once (decide, two rechecks, write).
8. **S15 finds a new holding** not on `company_list.csv` → add it, run it through S10-S14, then S15 again.

### recheck
1. **Setup and S1** with mode `recheck`; copy the last full run's `sector_map.md`, `sectors.json` and `sector_of.tsv` into the run folder (`s1_setup.md`).
2. **S4 stage numbers** (`sector_numbers.py --stage-only`) and **S5 in review mode**: only sector markers that are due, or whose machine-checked state changed, are reviewed; a sector marker that breaks marks every company in that sector for re-analysis and triggers a `full` run for that sector's map entry (tell the user).
3. **S9** (holdings plus every ticker in the sheet's Data tab), then one company at a time: S10 → S11.
   - S11 action `hold` → S14 records a verdict-history row ("markers held, results FYyyQn"); nothing else changes.
   - `verify` (a marker near its line, or a figure the script couldn't read) → S12, then S11 again on the verified figures.
   - `re-analyse` (a marker broken, the half-yearly full re-analysis due, a new holding with no thesis, or the user asks) → S12 → S13 → S13R1 → S13R2 → S14, as in full mode.
   - `integrity review` (a governance filing matched an integrity term) → S12 → S13 at once (the analysis reads the filing first); a confirmed integrity flag overrides every marker (rule 1.3) and the user is told straight away.
4. **S15 → S15R → S16** as in full mode.

## Run rules
- **Pending results:** companies are analysed on their latest declared results. At run start, create the sheet tab "Pending <FYyyQn> results" (replacing the previous quarter's; only one exists) and put its name in Data!BA1. S14 lists there the companies that haven't declared the run quarter. After the quarter's SEBI deadline, schedule a reminder to the user to re-run them.
- **Re-research:** a company is re-analysed only when S11 sends it (marker broken, integrity review, half-yearly re-analysis due: two newer quarters declared since the results its thesis used), when it has declared newer results in a full run, or when the user asks; a quarter passing isn't a reason by itself. An interrupted analysis is resumed from `status.csv`, not restarted. The sheet keeps a company's last row until its replacement completes.
- **Thesis markers:** every analysed company has 4-6 dated markers (sector-level and company-level) in `runs/theses/<SYM>.json`, written by `thesis_register.py` from the agreed analysis (S14). How a break is weighed against the position: `process/investing_rules.md` (exit rules).
- **Sector calls:** every sector entry S5 writes or changes is logged in `runs/sector_calls.csv` with its date, stage, horizon and markers (`sector_calls.py log`); each run's S5 records marker states, and `sector_calls.py score` reports the hit rate of past calls (markers held or broken by their dates; the sector's later median return against the market). The hit rate is reported to the user with every full run's map.
- **New full run:** S2-S5 again (S5 reviews, not rebuilds, the last map; `process/screens.json` is reviewed, not rebuilt), then companies flow as above, with S10 and S12 fetching only what is new.
- **Learnings:** after each S12, fold anything new in `process/fetch_learnings.md` into `s12_fetch.md` or `data_rules.md`; after each recheck, apply its learnings per `recheck.md`. Tell the user about changes that alter an agreed outcome.
- **Rules wording:** step files point to `process/investing_rules.md` and never restate it, so a rule change (such as the pending proposal in `runs/rule_changes_proposed.md`) needs no process edit unless an output field changes.

## Orchestrator duties
- **Claim the run:** one orchestrator per run. It writes at the top of `progress.md`: "Orchestrator: <session or thread>, since <time>, last update <time>", and refreshes the last-update time at every hand-off. Another session takes over only if the user asks, or the claim hasn't been updated for 2+ hours and that session is gone; it notes the takeover.
- **Brief each helper** with only its step file (plus what that file names), the run folder, the mode, and its company, batch or sector. When a helper finishes, start the next step's script or helper.
- **Before every hand-off** update `status.csv` and `progress.md`, so a new orchestrator can resume exactly:
  - `status.csv` columns: `sym, phase, state, stage, loops_to_s10, results_used, updated, note`. `phase` is S8-S16; `state` is queued / running / done / blocked; `stage` is main / recheck1 / recheck2 for S13, or the S11 action.
  - `progress.md`: the mode line and the claim line, then a checklist: steps done, running (with model), next, open items for the user. Short lines, no prose paragraphs. The thread's to-do list mirrors it.

## Run folders and shared files (`runs/`, git-ignored)
- `runs/<FYyyQn>/`: one folder per run, named after the latest quarter that has ended; the mode is the first line of its `progress.md`. A second run in the same quarter (a full run after that quarter's recheck run) gets the suffix `_full` (`runs/FY27Q2_full/`). Scripts take the run from `tools/scripts/config.py` (`RUN`, or the `RUN` environment variable, else the newest `runs/FY*`).
- Shared across runs: `runs/verdict_history.csv` (S14), `runs/theses/<SYM>.json` (S14), `runs/sector_calls.csv` (S5), `runs/playbooks/<sector>/` (S6-S7).
- `data/playbook/`: the playbook base data, kept for the playbooks (outcomes, features, business types, pattern results, experts, the sector test; `s6_playbook.md`). Scripts find it through `config.py` (`playbook_dir()`, or the `PLAYBOOK_DATA` environment variable). The working files of its 2026-11-03 build are in `archive/past_2026-11-03/` (never depended on).

## Resuming
1. Read `COMMON_AI.md` (and the agent-specific file), this file, the run's `progress.md` (mode first) and `status.csv`.
2. Take over the claim if allowed (above).
3. For each company, batch or sector marked running: check its output files. A complete output means the step finished: record it and move on. A partial one means the helper stopped: restart that step for that item, telling the helper which files exist. Scripts skip finished work (saved histories, statements, pages), so re-run their command.
4. Continue from the first queued item in the order of work for the run's mode.

## Caveats (stated with every sector call and playbook finding)
- **Survivorship:** screener's screens list only listed companies; delisted and merged names come from the delisted list and whatever screener still has.
- **Labels:** industry labels are today's NSE classification (screener's copy), not the one at a past date.
- **Old fundamentals:** screener's statements cover about 12 years; before them only chart features (growth, P/E, size, price) cover every company, and annual-report statements cover only what was parsed (`tools/ar_statements.md`).
- **Forward evidence only:** backward industry figures did not predict winning industries in the playbook base data, so a sector call rests on official forward evidence and is scored later, not trusted on its numbers.
