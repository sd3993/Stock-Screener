# S11R1.n, S11R2.n: analysis recheck checklist (deep tier, run per `/workflow/recheck.md`)

Work file: `runs/companies/<SYM>/<FYyyQn>/main.json` (the newest results-quarter folder; recheck 1) or `recheck<N-1>.json`; your output: `recheck<N>.json` and `.md` beside it. Read `/workflow/s11_analysis.md` first.

1. **Newer results:** has the company declared results newer than those used? If so, reply only `NEW_RESULTS: <FYyyQn>`.
2. **Figures:** every figure the verdict depends on, checked against the page it cites and against the cached screener figures (definition gaps ruled out first); every `facts_check.json` mismatch resolved; data flags complete.
3. **Math:** normalised trailing EPS (one-offs stripped), each EPS path's build, growth rates, exit P/E checks (a re-rating only on forward evidence).
4. **Non-negotiables:** each Pass / Bent / Fail tested against the exact wording of the non-negotiables and their sector notes (the promoter selling and buying rule's tests for any promoter sale or buying).
5. **Contrary evidence** for each verdict-deciding claim: guidance delivered or missed before (scorecard), order book and capacity claims against filings, every negative's temporary/structural call, peers' exit P/Es, the claim that the company captures its sector's tailwind (its own figures, not the sector's), the moat verdict against the moats rule's evidence and tests (no claim taken from the company's own words; a wide moat only moves inputs it is shown to support), and for a participant, that the emerging part enters the base case only as far as filed evidence backs it.
6. **What makes it unfavourable:** what would have to happen for the case to fall below the hurdle or for its visibility to end, and how likely that is (the trajectory rule's standard for the likelihood of scenarios); flag any base or bear case that departs from that standard.
7. **Missed evidence:** the latest results, call, presentation, shareholding, pledge and filings all read; the gate file's `for_s11` items answered; any negative not mentioned.
8. **Visibility and stage:** the visible-until date follows from the company's own evidence (the sector's duration only supports it), `years` follows from the date, and the stage is consistent with the evidence and the rules file's current wording.
9. **Markers:** each meets the exit rules and the thesis-marker standard (`/principles/sector_rules.md`); "script" markers use supported metrics.
10. **Status:** it follows the entry tests (a company not held) or the one exit test (a holding): no exit rests on a weak quarter, a price move or a high valuation alone; a watch names dated evidence; an exit states its urgency and the event behind it.
11. **History:** no forecast or judgement rests on a past pattern beyond what the use of history rule allows.
12. **Supplier:** a supplier's focus share is on filed evidence and each supplier risk is sized in the EPS paths, not just named.
13. **Promoter track record:** each part (delivery, group, capital allocation, minority treatment) rests on sources, and the verdict carries through: poor as an integrity flag, mixed in evidence quality and the exit P/E.
