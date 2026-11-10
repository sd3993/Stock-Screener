# S13R1.n, S13R2.n: analysis recheck checklist (deep tier, with `process/recheck.md`)

Work file: `<run>/analysis/<SYM>/main.json` (recheck 1) or `recheck<N-1>.json`; your output: `recheck<N>.json` and `.md` beside it. Read `process/s13_analysis.md` first.

1. **Newer results:** has the company declared results newer than those used? If so, reply only `NEW_RESULTS: <FYyyQn>`.
2. **Figures:** every figure the verdict depends on, checked against the page it cites and against the cached screener figures (definition gaps ruled out first); every `facts_check.json` mismatch resolved; data flags complete.
3. **Math:** normalised trailing EPS (one-offs stripped), each EPS path's build, growth rates, exit P/E checks, dividend.
4. **Non-negotiables:** each Pass / Bent / Fail tested against the exact wording of rule 1 and its sector notes (rule 1.2's tests for any promoter sale or buying).
5. **Contrary evidence** for each verdict-deciding claim: guidance delivered or missed before (scorecard), order book and capacity claims against filings, every negative's temporary/structural call, peers' exit P/Es, and the claim that the company captures its sector's tailwind (its own figures, not the sector's).
6. **What makes it unfavourable:** for each horizon given, what would have to happen for the case to fall below the hurdle or lose its horizon, and how likely that is (rule 2, "Likelihood of scenarios"). A broken thesis that is still favourable is rewritten, not rejected. Flag a base case that needs several uncertain things to all go right, and a bear case that stacks many bad things at once.
7. **Missed evidence:** the latest results, call, presentation, shareholding, pledge and filings all read; the gate file's `for_s13` items answered; any negative not mentioned.
8. **Horizon and stage:** consistent with the evidence, the sector entry's duration and the rules file's current wording.
9. **Markers:** 4-6, at least one sector-level and three company-level; each observable on its due date from a named source; thresholds where a miss would change the case; "script" markers use supported metrics.
