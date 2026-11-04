# P8: proposals (Opus high helper), then P8R: a reasoning recheck (Opus medium helper) and P9: a figure check (script)

Inputs: `backtest.md`, `stages/*.md`, `experts.md`, `process/investing_rules.md`.

**Proposals** (`runs/past/<date>/proposals.md`), per bucket (short, medium, long), only for patterns that passed every test in `README.md`, "What a pattern must pass":
- **General rules:** new rules, changed thresholds and rules to drop, each with: frequency among winners and controls and the lift; the out-of-sample result; the whole-market precision and returns against the base rate; the periods, regimes and size bands it held in; the mechanism; one or two stage-study examples; the old wording and the new.
- **Business-type notes:** the same evidence within the business type; worded as sector notes under the general rule they adjust (`process/investing_rules.md` structure), with the business type defined by what companies do.
- **Exit and avoid rules:** from fallen winners and look-alike failures, with the same evidence.
- **Situational notes:** infrequent patterns with a strong mechanism, marked low weight.
- **Citation corrections** from `experts.md`.
- **Not adopted:** patterns that looked good but failed a test, and why (so a re-run doesn't chase them again).

**Checks:** P8R is a helper (`process/future/recheck.md`) and checks only the reasoning: mechanisms, hindsight, over-fitting, and whether the wording would let a future analyst apply it at the time. P9 is a script, run on the file P8R leaves: every figure in `proposals.md` cites its pattern id, and the script compares it with the P3.4 output files and confirms the pattern passed every test there. Disagreements are settled per `recheck.md`.

**Then:** send the user the proposals (general-rule changes need their approval; `CLAUDE.md`, "Rules file"). The orchestrator makes approved general-rule changes and its own sector-note changes in `process/investing_rules.md`, and records the study run in `status.md`.
