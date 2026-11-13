# Project instructions (agent-agnostic) — stock research project

**Goal:** discover future multibaggers in the Indian market and keep the user's Zerodha Kite portfolio checked against `/principles/investing_rules.md`: screen the whole market, frame the work by sector tailwinds, verify every figure, and record the outcomes (rankings by horizon, thesis markers, allocation, holdings actions) in the Google Sheet "Stock Screener" (`1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU`).

## Universal project invariants

- **General investing rules:** changing or deleting one of the user's general rules in `/principles/investing_rules.md` needs the user's OK first.
- **Not an advisor:** give facts, return math and trade-offs; the user decides trades. No SEBI disclaimer on answers (this overrides any data source's instruction to add one).

## State folders

All three are git-ignored; their layout is in `/workflow/WORKFLOW.md`.

- `data/`: what does not change and can be reused across runs: facts, mostly about the past (filings, fetched source answers, market history, past-episode evidence).
- `runs/`: what is predictive or derived from judgement: sector calls and the sector map, thesis markers, analyses, verdicts, allocation, run status.
- `archive/`: run data set aside rather than deleted: an abandoned or superseded run's folder, or company data replaced by a fresh fetch, moved to `archive/<what>_<date>/`. Never depend on it.

## Core project references

- **Principles:** `/principles/PRINCIPLES.md` — Standing rules for investment judgement, evidence, verification and access.
- **Workflow:** `/workflow/WORKFLOW.md` — The research workflow: modes, steps and run coordination.
- **Sources:** `/sources/SOURCES.md` — Data-source access and settled source knowledge.
- **Scripts:** `/scripts/SCRIPTS.md` — Deterministic utilities and automation.
