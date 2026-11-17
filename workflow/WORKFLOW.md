# Workflow index

Entry point for the stock research workflow. How the orchestrator runs and resumes a run: `/workflow/orchestrator.md`.

## Two modes, one pipeline
- **`full`:** research from scratch: market-wide screens, the sector map (tailwinds and emerging sectors), gate, then every holding and survivor analysed. Run yearly, and at once when a sector marker breaks, a major policy is notified that touches a sector on the map or a preferred sector (the sector preferences rule), or the list runs thin (too few names passing the hurdle to fill the position size and count rule's targets).
- **`recheck`:** existing companies only (holdings and every name on the sheet's list or watchlist), each quarter after results. It is the same pipeline entered at the company list (S7) with the last full run's sector map; same step files, same status files. A script checks each company's thesis markers (S9); only companies it sends on get the fetch subagent and a new analysis.

Screening (S2, S3) is market-wide and the sector map never excludes a company: `/principles/sector_rules.md`.

## Universal workflow rules

- Tiers (script / light / standard / deep / deepest) are the global capability tiers (`~/.common-ai/COMMON_AI.md`); the step table gives each step's tier, with the reason wherever it is deepest.
- Outputs are in the run folder `runs/<FYyyQn>/` unless noted; a company's own judgement outputs are in `runs/companies/<SYM>/` (its thesis, marker-check history, and its analyses in one folder per results quarter, `runs/companies/<SYM>/<FYyyQn>/`).

## Steps

Every step has its own major number (S1…S14), in the order the steps run. A step that repeats is written X.0 here; its runs are X.1, X.2 … (never .0 for a real run): batches in order, per-company steps by the company's position in `company_list.csv` (`S11.3` is the third company). A recheck takes the number of what it checks (S6R.2 checks S6.2; S11R1.3 and S11R2.3 are S11.3's first and second rechecks). Labels: `/workflow/orchestrator.md`. In the File column, a file that holds several steps is followed by the step it holds.

| Step | Standard name | Mode(s) | Tier or script | File | Purpose |
|---|---|---|---|---|---|
| S1 | Setup and holdings | full, recheck | scripts `run.py setup`, `kite_holdings.py` | `s1_setup.md` | Opens the run and brings in the current holdings |
| S2 | Screens | full | script `screens.py run` | `s2_screens.md` | Sweeps the whole market through the screens |
| S3 | Triage | full | script `triage.py` | `s3_triage.md` | First numeric cut of the universe |
| S4 | Sector numbers | full; recheck (stage numbers only) | scripts `sectors.py syms`, `scr_company.py --only overview,shareholding`, `mb_history.py`, `sectors.py clusters`, `sectors.py stage` | `s4_sector_numbers.md` | Industry-level evidence for the sector map |
| S5 | Sector map | full (build or review); recheck (review due sector markers only) | deep; then scripts `sectors.py order`, `sectors.py log` | `s5_sector_map.md` | Maps sector tailwinds and emerging sectors, and orders the gate |
| S5R | Sector map recheck | full; recheck when a marker status changed | deep | `s5r_sector_recheck.md` | Independent check of the sector map |
| S6.0 | Gate | full | deep, batches of ~10, tailwind sectors first | `s6_gate.md` | Filters the universe before deep analysis |
| S6R.n | Gate recheck | full | deep | `s6r_gate_recheck.md` | Independent check of a gate batch |
| S7 | Company list | full, recheck | script `run.py list` | `s7_company_list.md` (S7) | Decides which companies are worked on, and in what order |
| S8.0 | Fetch scripts | full, recheck | scripts `scr_company.py`, `scr_docs.py`, one company | `s7_company_list.md` (S8.0), `s10_fetch.md` | Brings a company's source data up to date |
| S9.0 | Marker check | recheck | script `thesis.py check`, one company | `s9_marker_check.md` | Tests a company's thesis markers against new results |
| S10.0 | Fetch subagent | full; recheck (verify and re-analyse only) | standard, one company: exact figure extraction from filings (OCR-garbled scans, restated columns) decides verdicts, so not light until a light-tier trial on one company matches a standard-tier run figure for figure | `s10_fetch.md` | Completes and verifies a company's evidence |
| S11.0 | Deep analysis | full; recheck (re-analyse only) | deepest, one company: the verdict the user trades on, weighing many conflicting filings, guidance records and the sector case; two rechecks follow | `s11_analysis.md` | The verdict: thesis, visibility and return math |
| S11R1.n | Analysis recheck 1 | full, recheck | deep (deepest for an `unresolved` judgement call) | `s11r_analysis_recheck.md` | First independent check of an analysis |
| S11R2.n | Analysis recheck 2 | full, recheck | deep (deepest for an `unresolved` judgement call) | `s11r_analysis_recheck.md` | Second independent check of an analysis |
| S12.0 | Listing | full, recheck | scripts `thesis.py register`, `scr_company.py --only overview`, `sheet_write.py listing` (if the sheet can't be written: its `--dry-run` plan applied by a light-tier subagent, read back cell by cell) | `s12_listing.md` | Records agreed verdicts and thesis markers |
| S13 | Allocation | full, recheck | deep | `s13_allocation.md` (S13) | Position decisions against the investing rules |
| S13R | Allocation recheck | full, recheck | deep, rechecks 1 and 2 (S13R1, S13R2) | `s13r_allocation_recheck.md` | Independent checks of the allocation |
| S14 | Sheet write | full, recheck | script `sheet_write.py allocation` (fallback as S12) | `s13_allocation.md` (S14) | Records the allocation in the sheet |

Every recheck step also follows `recheck.md`.

## Workflow files

- [`orchestrator.md`](orchestrator.md) — Run coordination: sequencing, run state and recovery.
- [`s1_setup.md`](s1_setup.md) — Run initialisation and holdings intake.
- [`s2_screens.md`](s2_screens.md) — Whole-market screening.
- [`screens.json`](screens.json) — Screen definitions and the screening account's column set (input to S2).
- [`s3_triage.md`](s3_triage.md) — Numeric triage of the screened universe.
- [`s4_sector_numbers.md`](s4_sector_numbers.md) — Industry-level evidence gathering.
- [`s5_sector_map.md`](s5_sector_map.md) — Sector judgement, emerging-sector discovery and work ordering.
- [`s5r_sector_recheck.md`](s5r_sector_recheck.md) — Verification of the sector map.
- [`s6_gate.md`](s6_gate.md) — Pre-analysis gating of companies.
- [`s6r_gate_recheck.md`](s6r_gate_recheck.md) — Verification of gate decisions.
- [`s7_company_list.md`](s7_company_list.md) — Company selection, ordering and per-company data refresh.
- [`s9_marker_check.md`](s9_marker_check.md) — Quarterly thesis-marker monitoring.
- [`s10_fetch.md`](s10_fetch.md) — Per-company evidence collection and figure verification.
- [`fetch_learnings.md`](fetch_learnings.md) — Intake for fetch findings awaiting incorporation.
- [`s11_analysis.md`](s11_analysis.md) — Deep company analysis and verdicts.
- [`s11r_analysis_recheck.md`](s11r_analysis_recheck.md) — Verification of company analyses.
- [`s12_listing.md`](s12_listing.md) — Recording agreed verdicts.
- [`s13_allocation.md`](s13_allocation.md) — Portfolio allocation decisions and their recording.
- [`s13r_allocation_recheck.md`](s13r_allocation_recheck.md) — Verification of allocation decisions.
- [`recheck.md`](recheck.md) — Shared procedure for every judgement recheck.

## State folders

### Data folders (`data/`)

- `data/companies/<SYM>/`: everything about one company, shared across runs: documents and their text in quarter folders (`FY27Q1/` …), cached screener answers in `scr/`, BSE answers in `bse/`, and `index.json`, `facts.json`, `search_log.json`. `data/market/`: market-wide answers. `data/kite/`: holdings pulled from Kite (latest `holdings.csv` and dated copies). `data/playbook/`: market-wide price and P/E history, read by S4's stage numbers.

### Run folders and shared files (`runs/`, git-ignored)
- `runs/<FYyyQn>/`: one folder per run, named after the latest quarter that has ended; the mode is the first line of its `progress.md`. A second run in the same quarter (a full run after that quarter's recheck run) gets the suffix `_full` (`runs/FY27Q2_full/`). How scripts pick the run: `/scripts/SCRIPTS.md`.
- Run-scoped only, in `runs/<FYyyQn>/`: the run's progress and status, screens and triage, gate decisions, that run's sector map and allocation.
- Per company, across runs, in `runs/companies/<SYM>/`: `thesis.json` (the current thesis markers, S12), `marker_checks.csv` (S9 history), and `<FYyyQn>/` per results quarter the analysis used (S11 and its rechecks; the newest folder is the latest analysis). A recheck run works from these and the copied sector map alone.
- Shared across runs: `runs/verdict_history.csv` (S12), `runs/sector_calls.csv` and `runs/sector_marker_states.csv` (S5).
- Every path above comes from `scripts/config.py`, so a layout change is one edit there.
