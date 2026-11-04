# Multibagger study: map, order of work and resuming

A repeatable study that refines `process/investing_rules.md` from past Indian multibaggers: what they looked like before and during their runs, compared with similar-looking companies that didn't multiply. It ends in rule-change proposals per bucket (short ~1-2 years, medium ~3-5, long 5-7+). General-rule changes need the user's approval (`CLAUDE.md`, "Rules file").

**When to run:** first run Nov 2026 (task 2). Re-run when the user asks, or about yearly, or after a market regime change (a crash or a long slump), so the rules keep up with new winners. A re-run fetches only new history (P1 scripts skip saved companies unless `--refresh`).

Read by the orchestrator. Helpers get only their own step file plus what it names. Outputs go to `runs/past/<date>/`, `<date>` being the run's start date (scripts use the newest such folder, or `HIST_RUN=<date>`; a new run starts a new folder); the current run's progress is in `runs/past/<date>/status.md` (read it before resuming). Sources and scripts: `tools/tools.md`.

## What a pattern must pass (applies to every step)
The study looks for patterns that recur and can be seen at the time, not stories that only make sense in hindsight.
1. **Point in time:** measured only from data published before the window's start date. Results count from their filing date (or quarter end + 45 days, + 60 for Q4, when the filing date is unknown); price, P/E and TTM EPS are read from the chart series on that date. A pattern that depends on a figure restated later is flagged and not used.
2. **Frequency and lift:** each pattern gets its frequency (share of winners that had it) and its lift (share of winners with it ÷ share of matched controls with it). A pattern counts only when it is common among winners (frequency ≥ 50% for a general rule) **and** clearly more common than among controls (lift ≥ 1.5). Common in both, or rare, is not a rule.
3. **Reason required:** each kept pattern needs a mechanism that explains it (earnings growth plus re-rating, reinvestment at high returns, operating leverage, balance-sheet repair, etc.), backed by the stage studies or the expert evidence. A strong number with no reason is reported as "possibly chance" and doesn't become a rule.
4. **Out of sample:** patterns are found on windows starting 2006-2015 and tested unchanged on 2016-2023. A pattern must hold in more than one regime and size band. Thresholds are checked at nearby values (a cut-off that flips the result when moved a little is over-fitted). With ~20+ hypotheses tested, some look good by luck: consistency across periods outweighs one strong result.
5. **Whole-market test:** a candidate rule set is applied at each past date to every listed company, not only the sample, and scored on precision (the share of companies it passes that went on to multiply), against the base rate, and on their returns against the market.
6. **Business type, from what the company actually does:** every pattern is scored for the whole sample and per business type. A business type is set by the economics that drive results (`p2_sample.md`, "Business type"), read from the business description, segments and revenue drivers, never taken from screener's or any other provider's sector label. A pattern that fails overall but passes 1-5 within a business type becomes a business-type note (a sector note in `process/investing_rules.md`); a pattern that fails in one type is not discarded for the others.
7. **Infrequent patterns** (turnarounds, spin-offs, one-off windfalls) stay low-weight situational notes, kept only with a strong mechanism; never general rules.
8. **Exit and avoid signals** come the same way, from patterns common in fallen winners and in look-alike failures.

## Steps
Every step has its own major number. A step that repeats (rounds, batches, one company at a time) is written X.0 here; its runs are X.1, X.2 … in order (never .0 for a real run), and a recheck takes the number of what it checks (P10R.3 checks P10.3). Labels: `CLAUDE.md`, "Labels". Outputs are in `runs/past/<date>/` unless noted.

| Step | Standard name | Model / effort or script | File | Inputs | Outputs | Done when |
|---|---|---|---|---|---|---|
| P1 | Universe and outcomes | scripts (`scr_tool.py --login` screens, `mb_universe.py`, `mb_history.py`, `mb_outcomes.py`) | `p1_universe.md` | screener screens, delisted list, chart histories | `universe.csv`, `outcomes.csv`, `data/companies/<SYM>/scr/history.json` | every universe company has a history or a recorded failure; outcomes written |
| P2.0 | Sample | script (`mb_sample.py`), once per tagging round | `p2_sample.md` | `outcomes.csv`, industry labels (`scr/overview.json`), `business_types/batch_*.csv` | `sample_candidates.csv`, `needs_next.csv`, `sample.csv`, `business_types.csv`, `sample_checks.md` | ~400 companies, each with its reason and business type; checks pass |
| P3.0 | Business-type tagging | Opus medium, batches of ~25 | `p3_tagging.md` (+ `p2_sample.md`, "Business type") | `business_types/batch_<n>_input.csv` (`mb_tag_batch.py`), `scr/overview.json`, reports | `business_types/batch_<n>.csv` | every row of the batch tagged |
| P4.0 | Statements | script (`scr_company.py`) | `p4_statements.md` ("P4.0") | `sample.csv` (fetch order) | `data/companies/<SYM>/scr/` | every sample company fetched or its failure recorded |
| P5.0 | BSE shareholding | script (`bse_shp.py`) | `p4_statements.md` ("P5.0") | BSE codes in `scr/overview.json` | `data/companies/<SYM>/bse/shp/` | every company with a BSE code fetched |
| P6.0 | Annual-report statements | script (`ar_statements.py plan`, `fetch`, `queue`, `reparse`) | `p4_statements.md` ("P6.0") | `sample_candidates.csv`, `scr/documents.json`, `ar_links.csv`, helper files | parsed reports, `ar_missing.csv`, `ar_helper_queue.csv` | every needed report parsed or queued |
| P7.0 | Annual-report helpers | Sonnet low (browser link helper; fallback readers) | `p4_statements.md` ("P7.0"), `p7_ar_helpers.md` | `ar_missing.csv`, `ar_helper_queue.csv` | `ar_links.csv`, `ar_FY<yy>_helper.json` | both queues empty |
| P8 | Features and scoring | scripts (`mb_features.py`, scoring) | `p8_features.md` steps 1-3 | `sample.csv`, `business_types.csv`, `outcomes.csv`, statements, parsed reports, BSE shareholding, `experts.md`, `process/investing_rules.md` | `features.csv`, `features_coverage.md`, scores | every hypothesis scored in-sample, out-of-sample and on the whole market |
| P9 | Mechanisms | Opus medium | `p8_features.md` steps 4-5 | P8's surviving patterns, `experts.md` | `backtest.md` | every surviving pattern has a mechanism or is marked "possibly chance"; P10 picks written |
| P10.0 | Stage studies | Opus high, one company each | `p10_stages.md` | `backtest.md` picks, the company's filings | `stages/<SYM>.md` | ~30 winners and ~10 fallen winners studied |
| P10R.n | Stage-study recheck | Opus medium, one each | `p10_stages.md` ("Recheck") | `stages/<SYM>.md`, cited documents | corrections in `stages/<SYM>.md` | every study rechecked |
| P11 | Experts | Opus medium (web) | `p11_experts.md` | published studies | `experts.md` | findings and hypotheses written, tagged with sources |
| P12 | Proposals | Opus high | `p12_proposals.md` | `backtest.md`, `stages/*.md`, `experts.md`, `process/investing_rules.md` | `proposals.md` | proposals written |
| P12R | Recheck | Opus medium | `p12_proposals.md` ("Checks") | `proposals.md` | `proposals.md` | agreed per `process/future/recheck.md` |
| P13 | Figure check | script | `p12_proposals.md` ("Checks") | `proposals.md`, P8 outputs | `proposals.md` | every figure matches the P8 outputs; sent to the user |

## Order of work
1. P11 can run any time (it needs no data). P1 next; its history fetch runs for hours in the background, watched by a half-hourly watchdog (`CLAUDE.md`, "Watchdog").
2. P2 → P3 → P2 …: each P2 round builds a tagging round's input, P3 batches tag it, the next P2 round finalizes and builds the next input, until every winner has a same-type control or no candidates left. Then P4 → P5 → P6, and P7 on the queues P6 writes, then back to P6 (`fetch`, `queue`) until both queues are empty (the P6 ⇄ P7 loop) → P8, once, after the loop → P9. P8's hypothesis list comes from `experts.md` (P11) plus the current rules; when P8 needs more companies tagged, they go back to P3.
3. P10, one helper at a time, each followed by its recheck (P10R.n); learnings from one study go into the next helper's brief. P10 picks come from P9's `backtest.md` (winners that the rules missed and that they caught, and fallen winners).
4. P12 after P9 and P10, then P12R, then P13. The proposals go to the user; approved general-rule changes and the orchestrator's sector-note changes are made in `process/investing_rules.md`.
5. Update `status.md` at every step boundary (it stays out of git with the rest of the run; `CLAUDE.md`, "Git"). Commit and push process or script changes made along the way.

## Resuming
Read `status.md`. Scripts skip finished work (saved histories, saved statements), so re-run the step's command. A stage study with a written `stages/<SYM>.md` but no recheck goes straight to its recheck. Batch numbers carry on from the last one in `status.md` (the next P3 batch after P3.37 is P3.38).

## Caveats (stated with every finding)
- **Survivorship:** screener's screens list only listed companies; delisted and merged names come from the delisted list and whatever screener still has. The gap is stated.
- **Regimes:** results split by start period; a pattern that works in one period only is reported as such.
- **Thin long windows:** sample sizes are shown with every figure.
- **Restatement:** statements are today's restated figures; valuation and EPS use the chart series as of each date.
