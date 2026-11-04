# Multibagger study: map, order of work and resuming

A repeatable study that refines `process/investing_rules.md` from past Indian multibaggers: what they looked like before and during their runs, compared with similar-looking companies that didn't multiply. It ends in rule-change proposals per bucket (short ~1-2 years, medium ~3-5, long 5-7+). General-rule changes need the user's approval (`CLAUDE.md`, "Rules file").

**When to run:** first run Nov 2026 (task 2). Re-run when the user asks, or about yearly, or after a market regime change (a crash or a long slump), so the rules keep up with new winners. A re-run fetches only new history (P1.1 scripts skip saved companies unless `--refresh`).

Read by the orchestrator. Helpers get only their own step file plus what it names. Outputs go to `runs/past/<date>/`, `<date>` being the run's start date (scripts use the newest such folder, or `HIST_RUN=<date>`; a new run starts a new folder); the current run's progress is in `runs/past/<date>/status.md` (read it before resuming). Sources and scripts: `tools/tools.md`.

## What a pattern must pass (applies to every step)
The study looks for patterns that recur and can be seen at the time, not stories that only make sense in hindsight.
1. **Point in time:** measured only from data published before the window's start date. Results count from their filing date (or quarter end + 45 days, + 60 for Q4, when the filing date is unknown); price, P/E and TTM EPS are read from the chart series on that date. A pattern that depends on a figure restated later is flagged and not used.
2. **Frequency and lift:** each pattern gets its frequency (share of winners that had it) and its lift (share of winners with it ÷ share of matched controls with it). A pattern counts only when it is common among winners (frequency ≥ 50% for a general rule) **and** clearly more common than among controls (lift ≥ 1.5). Common in both, or rare, is not a rule.
3. **Reason required:** each kept pattern needs a mechanism that explains it (earnings growth plus re-rating, reinvestment at high returns, operating leverage, balance-sheet repair, etc.), backed by the stage studies or the expert evidence. A strong number with no reason is reported as "possibly chance" and doesn't become a rule.
4. **Out of sample:** patterns are found on windows starting 2006-2015 and tested unchanged on 2016-2023. A pattern must hold in more than one regime and size band. Thresholds are checked at nearby values (a cut-off that flips the result when moved a little is over-fitted). With ~20+ hypotheses tested, some look good by luck: consistency across periods outweighs one strong result.
5. **Whole-market test:** a candidate rule set is applied at each past date to every listed company, not only the sample, and scored on precision (the share of companies it passes that went on to multiply), against the base rate, and on their returns against the market.
6. **Business type, from what the company actually does:** every pattern is scored for the whole sample and per business type. A business type is set by the economics that drive results (`p1_sample.md`, "Business type"), read from the business description, segments and revenue drivers, never taken from screener's or any other provider's sector label. A pattern that fails overall but passes 1-5 within a business type becomes a business-type note (a sector note in `process/investing_rules.md`); a pattern that fails in one type is not discarded for the others.
7. **Infrequent patterns** (turnarounds, spin-offs, one-off windfalls) stay low-weight situational notes, kept only with a strong mechanism; never general rules.
8. **Exit and avoid signals** come the same way, from patterns common in fallen winners and in look-alike failures.

## Steps
| # | Step | Who | Model / effort | File | Output (`runs/past/<date>/`) | Done when |
|---|---|---|---|---|---|---|
| P1.1 | Universe, history and outcomes | scripts (screens through `scr_tool.py --login`) | orchestrator | `p1_universe.md` | `universe.csv`, `outcomes.csv` | every universe company has a history or a recorded failure; outcomes written |
| P1.2 | Sample: winners, controls, fallen winners (selection, repair, checks, finalize) | script | orchestrator | `p1_sample.md` | `sample_candidates.csv`, `needs_next.csv`, `sample.csv`, `business_types.csv` | ~400 companies, each with its reason and business type; checks pass |
| P2 | Business types, in batches | helpers | Opus medium | `p2_tagging_brief.md` (+ `p1_sample.md`, "Business type") | `business_types/batch_<n>.csv` | every row of the batch tagged |
| P3.1 | Statements for the sample | script | orchestrator | `p3_statements.md` | `data/companies/<SYM>/scr/` | every sample company fetched or its failure recorded |
| P3.2 | BSE shareholding | script (`bse_shp.py`) | orchestrator | `p3_statements.md` | `data/companies/<SYM>/bse/shp/` | every company with a BSE code fetched |
| P3.3 | Annual-report statements | script (`ar_statements.py plan`, `fetch`, `queue`) | orchestrator | `p3_statements.md` | parsed reports, `ar_missing.csv`, `ar_helper_queue.csv` | every needed report parsed or queued |
| P3.4 | Features, scoring, whole-market check | scripts | orchestrator | `p3_backtest.md` steps 1-3 | `features.csv` | every hypothesis scored in-sample, out-of-sample and on the whole market |
| P4 | Leftover annual reports: browser link helper and fallback readers | helpers | Sonnet low | `p3_statements.md`, `p4_ar_helper_brief.md` | `ar_links.csv`, `ar_FY<yy>_helper.json` | both queues empty |
| P5 | Mechanisms and `backtest.md` | helper | Opus medium | `p3_backtest.md` steps 4-5 | `backtest.md` | every surviving pattern has a mechanism or is marked "possibly chance"; P6 picks written |
| P6 | Stage studies, one company at a time | helper each | Opus high | `p6_stages.md` | `stages/<SYM>.md` | ~30 winners and ~10 fallen winners studied |
| P6R | Stage-study recheck | helper each | Opus medium | `p6_stages.md` ("Recheck") | corrections in `stages/<SYM>.md` | every study rechecked |
| P7 | Expert evidence | helper | Opus medium | `p7_experts.md` | `experts.md` | findings and hypotheses written, tagged with sources |
| P8 | Proposals | helper | Opus high | `p8_proposals.md` | `proposals.md` | proposals written |
| P8R | Reasoning recheck | helper | Opus medium | `p8_proposals.md` ("Checks") | `proposals.md` | agreed per `recheck.md` |
| P9 | Figure check | script | orchestrator | `p8_proposals.md` ("Checks") | `proposals.md` | every figure matches the P3.4 outputs; sent to the user |

## Order of work
1. P7 can run any time (it needs no data). P1.1 next; its history fetch runs for hours in the background, watched by a half-hourly watchdog (`CLAUDE.md`, "Watchdog").
2. P1.2 → P2 → P1.2 …: P1.2 builds each tagging round's input, P2 helpers tag it, P1.2 finalizes and builds the next round, until every winner has a same-type control or no candidates left. Then P3.1 → P3.2 → P3.3 → P3.4, and P4 on the queues P3.3 writes, then back to P3.3 (`fetch`, `queue`) and P3.4 (features re-run) until both queues are empty → P5. P3.4's hypothesis list comes from `experts.md` (P7) plus the current rules; when P3.4 needs more companies tagged, they go back to P2.
3. P6, one helper at a time, each followed by its recheck (P6R); learnings from one study go into the next helper's brief. P6 picks come from P5's `backtest.md` (winners that the rules missed and that they caught, and fallen winners).
4. P8 after P5 and P6, then P8R, then P9. The proposals go to the user; approved general-rule changes and the orchestrator's sector-note changes are made in `process/investing_rules.md`.
5. Update `status.md` at every step boundary (it stays out of git with the rest of the run; `CLAUDE.md`, "Git"). Commit and push process or script changes made along the way.

## Resuming
Read `status.md`. Scripts skip finished work (saved histories, saved statements), so re-run the step's command. A stage study with a written `stages/<SYM>.md` but no recheck goes straight to its recheck.

## Caveats (stated with every finding)
- **Survivorship:** screener's screens list only listed companies; delisted and merged names come from the delisted list and whatever screener still has. The gap is stated.
- **Regimes:** results split by start period; a pattern that works in one period only is reported as such.
- **Thin long windows:** sample sizes are shown with every figure.
- **Restatement:** statements are today's restated figures; valuation and EPS use the chart series as of each date.
