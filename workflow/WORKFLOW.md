# Workflow index

Single entry point for the stock research workflow: the two modes, the rules every step follows, the step table and the state folders. How the orchestrator runs and resumes a run: `/workflow/orchestrator.md`.

## Two modes, one pipeline
- **`full`:** research from scratch: market-wide screens, sector tailwind map, gate, then every holding and survivor analysed. Run yearly, and at once when a sector marker breaks, a major policy is notified that touches a sector on the map or a preferred sector (the sector preferences rule), or the list runs thin (fewer names passing the hurdle than the position size and count rule's position count needs).
- **`recheck`:** existing companies only (holdings and every name currently listed in the sheet), each quarter after results. It is the same pipeline entered at the company list (S9) with the last full run's sector map; same step files, same status files. A script checks each company's thesis markers (S11); only companies it sends on get the fetch subagent and a new analysis.

Screening is always market-wide (S2, S3), never sector-only, and the sector map frames and orders the work without excluding a company (`/principles/sector_rules.md`).

## Universal workflow rules

- Standing instructions and working preferences: `/COMMON_AI.md` (and the agent-specific file beside it).
- Investing rules: `/principles/investing_rules.md`.
- Where each data item comes from and what is settled about each source: `/sources/SOURCES.md`.
- Tiers (script / light / standard / deep / deepest) are the global capability tiers (`~/.common-ai/COMMON_AI.md`); each step uses the lightest tier that is accurate, and the step table gives each step's tier, with the reason wherever it is deepest.
- Outputs are in the run folder `runs/<FYyyQn>/` unless noted; a company's own judgement outputs are in `runs/companies/<SYM>/` (its thesis, marker-check history, and its analyses in one folder per results quarter, `runs/companies/<SYM>/<FYyyQn>/`). Each script's exact rules are in its `--help`.

## Steps

Every step has its own major number (S1…S16), in the order the steps run. A step that repeats is written X.0 here; its runs are X.1, X.2 … (never .0 for a real run): batches in order, per-company steps by the company's position in `company_list.csv` (`S13.3` is the third company), playbooks by the sector's position in `sectors.json`. A recheck takes the number of what it checks (S8R.2 checks S8.2; S13R1.3 and S13R2.3 are S13.3's first and second rechecks). Labels: `/workflow/orchestrator.md`. In the File column, a file that holds several steps is followed by the step it holds.

| Step | Standard name | Mode(s) | Tier or script | File | Purpose |
|---|---|---|---|---|---|
| S1 | Setup and holdings | full, recheck | scripts `run.py setup`, `kite_holdings.py` | `s1_setup.md` | Opens the run and brings in the current holdings |
| S2 | Screens | full | script `screens.py run` | `s2_screens.md` | Sweeps the whole market through the screens |
| S3 | Triage | full | script `triage.py` | `s3_triage.md` | First numeric cut of the universe |
| S4 | Sector numbers | full; recheck (stage numbers only) | scripts `sectors.py syms`, `scr_company.py --only overview,shareholding`, `mb_history.py`, `sectors.py clusters`, `sectors.py stage` | `s4_sector_numbers.md` | Industry-level evidence for the sector map |
| S5 | Sector tailwind map | full (build or review); recheck (review due sector markers only) | deep; then scripts `sectors.py order`, `sectors.py log` | `s5_sector_map.md` | Frames and orders the work by sector tailwinds |
| S5R | Sector map recheck | full; recheck when a marker status changed | deep | `s5r_sector_recheck.md` | Independent check of the sector map |
| S6.0 | Playbook data | full, chosen sectors | scripts `mb_history.py`, `mb_outcomes.py`, `mb_features.py`, `mb_sector_test.py`, `sectors.py episodes` | `s6_playbook.md` (S6) | Historical episode data for a chosen sector |
| S7.0 | Sector playbook | full, chosen sectors | deepest, one sector: it writes the sector notes every later analysis in that sector applies, weighing past episodes read strictly without hindsight; a few a year | `s6_playbook.md` (S7) | Lessons from past tailwind episodes, as sector notes |
| S7R.n | Playbook recheck | full | deep | `s6_playbook.md` (S7R) | Independent check of a playbook |
| S8.0 | Gate | full | deep, batches of ~10, tailwind sectors first | `s8_gate.md` | Filters the universe before deep analysis |
| S8R.n | Gate recheck | full | deep | `s8r_gate_recheck.md` | Independent check of a gate batch |
| S9 | Company list | full, recheck | script `run.py list` | `s9_company_list.md` (S9) | Decides which companies are worked on, and in what order |
| S10.0 | Fetch scripts | full, recheck | scripts `scr_company.py`, `scr_docs.py`, one company | `s9_company_list.md` (S10.0), `s12_fetch.md` | Brings a company's source data up to date |
| S11.0 | Marker check | recheck | script `thesis.py check`, one company | `s11_marker_check.md` | Tests a company's thesis markers against new results |
| S12.0 | Fetch subagent | full; recheck (verify and re-analyse only) | standard, one company: exact figure extraction from filings (OCR-garbled scans, restated columns) decides verdicts, so not light until a light-tier trial on one company matches a standard-tier run figure for figure | `s12_fetch.md` | Completes and verifies a company's evidence |
| S13.0 | Deep analysis | full; recheck (re-analyse only) | deepest, one company: the verdict the user trades on, weighing many conflicting filings, guidance records and the sector case; two rechecks follow | `s13_analysis.md` | The verdict: horizon, thesis and return math |
| S13R1.n | Analysis recheck 1 | full, recheck | deep (deepest for an `unresolved` judgement call) | `s13r_analysis_recheck.md` | First independent check of an analysis |
| S13R2.n | Analysis recheck 2 | full, recheck | deep (deepest for an `unresolved` judgement call) | `s13r_analysis_recheck.md` | Second independent check of an analysis |
| S14.0 | Listing | full, recheck | scripts `thesis.py register`, `scr_company.py --only overview`, `sheet_write.py listing` (if the sheet can't be written: its `--dry-run` plan applied by a light-tier subagent, read back cell by cell) | `s14_listing.md` | Records agreed verdicts and thesis markers |
| S15 | Allocation | full, recheck | deep | `s15_allocation.md` (S15) | Position decisions against the investing rules |
| S15R | Allocation recheck | full, recheck | deep, rechecks 1 and 2 (S15R1, S15R2) | `s15r_allocation_recheck.md` | Independent checks of the allocation |
| S16 | Sheet write | full, recheck | script `sheet_write.py allocation` (fallback as S14) | `s15_allocation.md` (S16) | Records the allocation in the sheet |

Every recheck step also follows `recheck.md`.

## Workflow files

- [`orchestrator.md`](orchestrator.md) — Run coordination: sequencing, run state and recovery.
- [`s1_setup.md`](s1_setup.md) — Run initialisation and holdings intake.
- [`s2_screens.md`](s2_screens.md) — Whole-market screening.
- [`screens.json`](screens.json) — Screen definitions and the screening account's column set (input to S2).
- [`s3_triage.md`](s3_triage.md) — Numeric triage of the screened universe.
- [`s4_sector_numbers.md`](s4_sector_numbers.md) — Industry-level evidence gathering.
- [`s5_sector_map.md`](s5_sector_map.md) — Sector tailwind judgement and work ordering.
- [`s5r_sector_recheck.md`](s5r_sector_recheck.md) — Verification of the sector map.
- [`s6_playbook.md`](s6_playbook.md) — Historical sector playbooks and their verification.
- [`ar_statements.md`](ar_statements.md) — Procedure for obtaining statements older than the main source covers.
- [`s8_gate.md`](s8_gate.md) — Pre-analysis gating of companies.
- [`s8r_gate_recheck.md`](s8r_gate_recheck.md) — Verification of gate decisions.
- [`s9_company_list.md`](s9_company_list.md) — Company selection, ordering and per-company data refresh.
- [`s11_marker_check.md`](s11_marker_check.md) — Quarterly thesis-marker monitoring.
- [`s12_fetch.md`](s12_fetch.md) — Per-company evidence collection and figure verification.
- [`fetch_learnings.md`](fetch_learnings.md) — Intake for fetch findings awaiting incorporation.
- [`s13_analysis.md`](s13_analysis.md) — Deep company analysis and verdicts.
- [`s13r_analysis_recheck.md`](s13r_analysis_recheck.md) — Verification of company analyses.
- [`s14_listing.md`](s14_listing.md) — Recording agreed verdicts.
- [`s15_allocation.md`](s15_allocation.md) — Portfolio allocation decisions and their recording.
- [`s15r_allocation_recheck.md`](s15r_allocation_recheck.md) — Verification of allocation decisions.
- [`recheck.md`](recheck.md) — Shared procedure for every judgement recheck.

## State folders

### Data folders (`data/`)

- `data/companies/<SYM>/`: everything about one company, shared across runs: documents and their text in quarter folders (`FY27Q1/` …), cached screener answers in `scr/`, BSE answers in `bse/`, and `index.json`, `facts.json`, `search_log.json`. `data/market/`: market-wide answers. `data/kite/`: holdings pulled from Kite (latest `holdings.csv` and dated copies). `data/playbook/`: the playbook base data (market-wide history and the evidence drawn from it), with each sector playbook in `data/playbook/sectors/<sector>/` (past tailwind episodes: historical evidence, reused across runs; layout: `s6_playbook.md`). The working files of its 2026-11-03 build are in `archive/past_2026-11-03/` (never depended on).

### Run folders and shared files (`runs/`, git-ignored)
- `runs/<FYyyQn>/`: one folder per run, named after the latest quarter that has ended; the mode is the first line of its `progress.md`. A second run in the same quarter (a full run after that quarter's recheck run) gets the suffix `_full` (`runs/FY27Q2_full/`). Scripts take the run from `scripts/config.py` (`RUN`, or the `RUN` environment variable, else the newest `runs/FY*`).
- Run-scoped only, in `runs/<FYyyQn>/`: the run's progress and status, screens and triage, gate decisions, that run's sector map and allocation.
- Per company, across runs, in `runs/companies/<SYM>/`: `thesis.json` (the current thesis markers, S14), `marker_checks.csv` (S11 history), and `<FYyyQn>/` per results quarter the analysis used (S13 and its rechecks; the newest folder is the latest analysis). A recheck run works from these and the copied sector map alone.
- Shared across runs: `runs/verdict_history.csv` (S14), `runs/sector_calls.csv` and `runs/sector_marker_states.csv` (S5).
- Every path above comes from `scripts/config.py`, so a layout change is one edit there.
