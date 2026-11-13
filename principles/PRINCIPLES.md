# Principles index

Single entry point for the project's standing rules: what holds across all of them, then one line per principles file.

## Cross-cutting invariants

- **Instruction placement:** each instruction lives in exactly one place: the workflow and orchestration in `/workflow/WORKFLOW.md` and `/workflow/orchestrator.md`, step work in the step files (`/workflow/s*.md`) and the shared recheck procedure in `/workflow/recheck.md`, investing rules in `/principles/investing_rules.md`, sector, thesis-marker and playbook standards in `/principles/sector_rules.md`, triage and gate standards in `/principles/filter_rules.md`, data rules in `/principles/data_rules.md`, recheck standards in `/principles/recheck_rules.md`, source and account rules in `/principles/access_rules.md`, source how-to and the sheet's layout in `/sources/`, scripts in `/scripts/SCRIPTS.md` and each script's `--help`.
- **Git:** the remote is `origin` (https://github.com/sd3993/Stock-Screener). Only the workflow is in git (`/COMMON_AI.md`, the agent-specific project files and settings listed in them, `/principles/`, `/workflow/`, `/sources/`, `/scripts/`); run outputs and fetched data are not. Retired committed files (principles, workflow, sources, scripts) are deleted, not archived: git history keeps them. Run data isn't in git, so it goes to `archive/` instead (`/COMMON_AI.md`).

## Principles reference

- [`investing_rules.md`](investing_rules.md) — Investment judgement: return hurdles, quality gates and position governance.
- [`sector_rules.md`](sector_rules.md) — Sector framing, discovery stage, thesis markers, business typing and historical playbook evidence.
- [`filter_rules.md`](filter_rules.md) — Pre-analysis filtering: what triage and the gate may reject, and on what evidence.
- [`data_rules.md`](data_rules.md) — Evidence admissibility, source precedence and company-data storage.
- [`recheck_rules.md`](recheck_rules.md) — Verification standards for rechecked judgement work.
- [`access_rules.md`](access_rules.md) — Source dependency, account and credential boundaries, and outcome-store discipline.
