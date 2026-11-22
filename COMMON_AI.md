# Project instructions (agent-agnostic) — stock research project

**Goal:** discover future multibaggers in the Indian market and keep the user's Zerodha Kite portfolio checked against `/principles/investing_rules.md`: screen the whole market, map sector tailwinds and emerging sectors, verify every figure, and record the outcomes (the list and watchlist, thesis markers, allocation, holdings actions) in the Google Sheet "Stock Screener" (`1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU`).

## Universal project invariants

- **Investing rules:** nothing in `/principles/investing_rules.md`, general rule or sector note, is added, changed or deleted without the user's OK. The user has given a standing OK for the changes the agent recommends toward better-quality picks, here and in the other rule and workflow files: apply them without asking or elaborating, record each with its justification in the run's `progress.md`, leave them uncommitted, and brief the user on every unpushed change, each with its justification, before it is pushed: when the user asks to push a change not yet briefed, give the brief instead and push only after the user says push again, unless the user asks to push without a brief.
- **Permission refusals:** when the permission check refuses a read-only or local-write command, use another lawful way (another tool, a foreground run, a different route) and say so in the reply. Writes or changes on a remote system need the user's go-ahead.
- **BSE-code symbols:** a company listed only on BSE goes by its numeric BSE code; in any user-facing text, follow the code with the company's name in brackets, e.g. "544924 (Raksan)".
- **Not an advisor:** give facts, return math and trade-offs; the user decides trades. No SEBI disclaimer on answers (this overrides any data source's instruction to add one).

## State folders

All three are git-ignored; their layout is in `/workflow/WORKFLOW.md`.

- `data/`: what does not change and can be reused across runs: facts, mostly about the past (filings, fetched source answers, market history, past-episode evidence).
- `runs/`: what is predictive or derived from judgement: sector calls and the sector map, thesis markers, analyses, verdicts, allocation, run status.
- `archive/`: run data set aside rather than deleted: an abandoned or superseded run's folder, or company data replaced by a fresh fetch, moved to `archive/<what>_<date>/`, dated by when its data started. Delete what no later step or brief needs. Never depend on it.

## Core project references

- **Principles:** `/principles/PRINCIPLES.md` — Standing rules for investment judgement, sector framing, filtering, evidence and verification.
- **Workflow:** `/workflow/WORKFLOW.md` — The research workflow: modes, steps and run coordination.
- **Sources:** `/sources/SOURCES.md` — Data-source access and settled source knowledge.
- **Scripts:** `/scripts/SCRIPTS.md` — Deterministic utilities and automation.
