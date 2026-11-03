# Multibagger study: map, order of work and resuming

A repeatable study that refines `process/investing_rules.md` from past Indian multibaggers: what they looked like before and during their runs, compared with similar-looking companies that didn't multiply. It ends in rule-change proposals per bucket (short ~1-2 years, medium ~3-5, long 5-7+). General-rule changes need the user's approval (`CLAUDE.md`, "Rules file").

**When to run:** first run Nov 2026 (task 2). Re-run when the user asks, or about yearly, or after a market regime change (a crash or a long slump), so the rules keep up with new winners. A re-run fetches only new history (step 1 scripts skip saved companies unless `--refresh`).

Read by the orchestrator. Helpers get only their own step file plus what it names. Outputs go to `studies/multibaggers/`; the current run's progress is in `studies/multibaggers/status.md` (read it before resuming). Sources and scripts: `tools/tools.md`.

## What a pattern must pass (applies to every step)
The study looks for patterns that recur and can be seen at the time, not stories that only make sense in hindsight.
1. **Point in time:** measured only from data published before the window's start date. Results count from their filing date (or quarter end + 45 days, + 60 for Q4, when the filing date is unknown); price, P/E and TTM EPS are read from the chart series on that date. A pattern that depends on a figure restated later is flagged and not used.
2. **Frequency and lift:** each pattern gets its frequency (share of winners that had it) and its lift (share of winners with it ÷ share of matched controls with it). A pattern counts only when it is common among winners (frequency ≥ 50% for a general rule) **and** clearly more common than among controls (lift ≥ 1.5). Common in both, or rare, is not a rule.
3. **Reason required:** each kept pattern needs a mechanism that explains it (earnings growth plus re-rating, reinvestment at high returns, operating leverage, balance-sheet repair, etc.), backed by the stage studies or the expert evidence. A strong number with no reason is reported as "possibly chance" and doesn't become a rule.
4. **Out of sample:** patterns are found on windows starting 2006-2015 and tested unchanged on 2016-2023. A pattern must hold in more than one regime and size band. Thresholds are checked at nearby values (a cut-off that flips the result when moved a little is over-fitted). With ~20+ hypotheses tested, some look good by luck: consistency across periods outweighs one strong result.
5. **Whole-market test:** a candidate rule set is applied at each past date to every listed company, not only the sample, and scored on precision (the share of companies it passes that went on to multiply), against the base rate, and on their returns against the market.
6. **Business type, from what the company actually does:** every pattern is scored for the whole sample and per business type. A business type is set by the economics that drive results (`s2_sample.md`, "Business type"), read from the business description, segments and revenue drivers, never taken from screener's or any other provider's sector label. A pattern that fails overall but passes 1-5 within a business type becomes a business-type note (a sector note in `process/investing_rules.md`); a pattern that fails in one type is not discarded for the others.
7. **Infrequent patterns** (turnarounds, spin-offs, one-off windfalls) stay low-weight situational notes, kept only with a strong mechanism; never general rules.
8. **Exit and avoid signals** come the same way, from patterns common in fallen winners and in look-alike failures.

## Steps
| # | Step | Who | Model / effort | File | Output (`studies/multibaggers/`) | Done when |
|---|---|---|---|---|---|---|
| S1 | Universe, history and outcomes | scripts (+ MCP screens) | orchestrator | `s1_universe.md` | `universe.csv`, `outcomes.csv` | every universe company has a history or a recorded failure; outcomes written |
| S2 | Sample: winners, controls, fallen winners; business types | script, helpers (types in batches, then review) | Opus medium | `s2_sample.md` | `sample.csv`, `business_types.csv` | ~400 companies, each with its reason and business type; review done |
| S3 | Statements for the sample | script | none | `s3_statements.md` | `data/companies/<SYM>/scr/` | every sample company fetched or its failure recorded |
| S4 | Pattern back-test | script, then orchestrator | Opus medium | `s4_backtest.md` | `features.csv`, `backtest.md` | every hypothesis scored in-sample, out-of-sample and on the whole market |
| S5 | Stage studies, one company at a time | helper each, + one recheck | Opus high (recheck Opus medium) | `s5_stages.md` | `stages/<SYM>.md` | ~30 winners and ~10 fallen winners studied and rechecked |
| S6 | Expert evidence | helper | Opus medium | `s6_experts.md` | `experts.md` | findings and hypotheses written, tagged with sources |
| S7 | Proposals, then rechecks 1 and 2 | orchestrator, helper each | Opus high (rechecks Opus medium) | `s7_proposals.md` | `proposals.md` | both rechecks agree; sent to the user |

## Order of work
1. S6 can run any time (it needs no data). S1 next; its history fetch runs for hours in the background, watched by a half-hourly watchdog (`CLAUDE.md`, "Watchdog").
2. S2 → S3 → S4. S4's hypothesis list comes from `experts.md` (S6) plus the current rules.
3. S5, one helper at a time, each followed by its recheck; learnings from one study go into the next helper's brief. S5 picks come from S4's results (winners that the rules missed and that they caught, and fallen winners).
4. S7 after S4 and S5. The proposals go to the user; approved general-rule changes and the orchestrator's sector-note changes are made in `process/investing_rules.md`.
5. Update `status.md` at every step boundary, and commit and push at each completed step (`CLAUDE.md`, "Git").

## Resuming
Read `status.md`. Scripts skip finished work (saved histories, saved statements), so re-run the step's command. A stage study with a written `stages/<SYM>.md` but no recheck goes straight to its recheck.

## Caveats (stated with every finding)
- **Survivorship:** screener's screens list only listed companies; delisted and merged names come from the delisted list and whatever screener still has. The gap is stated.
- **Regimes:** results split by start period; a pattern that works in one period only is reported as such.
- **Thin long windows:** sample sizes are shown with every figure.
- **Restatement:** statements are today's restated figures; valuation and EPS use the chart series as of each date.
