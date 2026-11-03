# Task 2: what past Indian multibaggers looked like, per horizon

Goal: test `process/investing_rules.md` against what past Indian multibaggers looked like before and during their runs, compared with similar-looking companies that didn't multiply, and propose rule changes per bucket (short ~1-2 y, medium ~3-5 y, long 5-7+ y). General-rule changes go to the user for approval (`CLAUDE.md`, "Rules file").

## Data (re-planned 3 Nov 2026 on screener.in; no Tapetide calls needed)
- **Universe:** screener screens through the MCP, in market-cap bands; each 200-row page is saved to a file and never read into context. The universe gives every listed company's symbol and screener id.
- **History per company, from screener's public chart API** (`tools/scripts/mb_history.py`; no login, no model tokens, about 3 requests a company). Covers back to about 2005:
  - price and volume (sampled about weekly over the long range);
  - daily P/E, with the TTM EPS behind it (one point per results date);
  - market cap to sales, with TTM sales, so market cap = ratio × sales.

  Merged and delisted companies are covered: HDFC to Jul 2023, GRUH to Oct 2019.
- **Statements per company** (`tools/scripts/scr_company.py`, also no model tokens): 12 years annual, 13 quarters, 12 quarters of shareholding, NSE announcements, and the annual-report list with exchange links back to about 2013.
- **Not available:**
  - Point-in-time restatement history: figures are as screener shows them today. Valuation at a date uses the P/E and TTM EPS series on that date.
  - Shareholding before the last 12 quarters: read from BSE shareholding patterns in the stage studies only.
  - A full list of delisted companies: screener's screens cover listed names only. Delisted candidates come from Tapetide's cached master list (136, `data/market/reference_stocks_delisted.json`) plus NSE/BSE delisting lists, then their screener pages.

## Method
1. **Universe and outcomes (MCP screens, then `mb_history.py` for every company; then a script).**
   - For every listed company with a market cap over ₹50 cr today, plus the delisted candidates: market cap and price multiples over every 2-, 3-, 5-, 7- and 10-year window starting each quarter from 2006.
   - The per-share price multiple is checked against the market-cap multiple to flag dilution.
   - Output: `outcomes.csv`.
2. **Sample (script, then an Opus medium review).** Per horizon:
   - **Winners:** short = 2x+ in 2 years; medium = 3x+ in 5 years (about 25% CAGR, the hurdle) and 5x+ as the strong group; long = 10x+ in 7-10 years.
   - **Controls:** about 1:1 non-winners that looked similar at the window's start (same start date, market-cap band and sector, similar starting ROCE, growth and P/E).
   - **Fallen winners:** names that multiplied and then gave back more than 50%, to test the exit rules.
   - **Delisted and merged names** wherever covered.
   - **Window starts** spread across 2006-2023, so the 2008 crash, the 2011-13 slump, the 2018-19 mid-cap bear market, the 2020 crash and the 2023-24 boom each show up.
   - Target about 400 companies. Output: `sample.csv`, with each pick's reason.
3. **Statements for the sample:** `scr_company.py` per company, about 400 runs, no model tokens.
4. **Rule back-test (script).**
   - For each company and window start, compute what the rules could see on that date from the statements and the chart series: size, growth and acceleration (TTM EPS and sales series), ROCE, cash conversion, debt tests, P/E against its own 5-year median (P/E series), PEG, dilution.
   - Score each rule per horizon: winners it would have rejected (missed winners) and controls it would have passed (false alarms), by period and by size band.
   - Output: `features.csv`, `rule_backtest.md`.
5. **Stage studies (helper per company, Opus high; one at a time).**
   - About 30 winners (10 per horizon) and about 10 fallen winners.
   - Each helper reads only documents dated before each stage (annual reports from screener's list back to about 2013, transcripts and results from BSE/NSE; all free) to avoid hindsight.
   - It classifies the stages (overlooked, earnings turn, re-rating, compounding, de-rating), their triggers and how long each lasted, and what an investor could have seen at the time.
   - Each study gets one recheck (Opus medium, `process/recheck.md`).
   - Output: `stages/<SYM>.md`.
6. **Expert evidence (helper, Opus medium; web):** India-specific multibagger studies by named practitioners (MOSL Wealth Creation Studies, Marcellus/Mukherjea, Mayer, Phelps, Kedia; IIM-A factor data), tagged per `process/investing_rules.md`. Output: `experts.md`.
7. **Synthesis (Opus high), then rechecks 1 and 2 (Opus medium).**
   - Rule-change proposals per bucket, each with:
     - the evidence: hit rates, examples, and which period it holds in;
     - the old wording and the new.
   - Output: `proposals.md`.
   - The user approves general rules; sector notes follow the usual rule.

## Caveats and how they're handled
- **Survivorship bias:** matched controls, merged and delisted names where covered, fallen winners. The remaining gap (delisted names not found) is stated with each finding.
- **Regimes:** results are split by start period. A rule that works in only one period is reported as such.
- **Thin data for long windows:** sample sizes are shown.
- **Hindsight:** valuation from the series as of each date; stage studies read only documents dated before each stage. Statements are today's restated figures: an effect that depends on a restated year is flagged.

## Cost and order
- **Tapetide:** none needed.
- **Screener:**
  - about 25 MCP screen pages (about 300 tokens each);
  - about 3 public chart requests per company for some 5,000 companies (a few hours of script time, paced by the library);
  - about 400 statement runs.
- **Claude usage:** mainly the stage studies (about 40 Opus high helpers and their rechecks), the expert-evidence helper and the synthesis.
- **Order:**
  - phase 6 alongside phase 1;
  - phase 2;
  - phases 3 and 4;
  - phase 5 (one helper at a time);
  - phase 7.

## Status
- 3 Nov 2026: the user paused task 2 over Tapetide's cost, then switched the project to screener.in and asked to continue. This plan is the re-plan on screener.
- **3 Nov 2026, phase 1 under way:**
  - universe pulled: 5,543 listed and 136 delisted candidates, in `universe.csv`; pages are in `universe/`;
  - `mb_history.py --csv studies/multibaggers/universe.csv` is running in the background, about 7 hours (log in the session scratchpad). Re-running it skips saved companies.
- **Phase 6 done:** `experts.md` holds 34 findings, 20 back-test hypotheses (H1-H20), and 4 corrections to the expert citations in rules 6, 8 and 9. The corrections go into `proposals.md` for the user's approval; the rules file is not edited directly.
- **Session restarted, 3 Nov 2026 ~10:40:** the history fetch stopped at 2915 of 5,679 companies. On resume:
  - re-run `uvx --from screener-mcp==0.5.0 python tools/scripts/mb_history.py --csv studies/multibaggers/universe.csv` in the background (it skips saved companies), and re-create the half-hourly watchdog;
  - when it ends, run `python tools/scripts/mb_outcomes.py`, then phase 2 (sample).
