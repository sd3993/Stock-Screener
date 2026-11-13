# Recheck: how every recheck runs (with the step's own checklist)

Every recheck meets the standards in `/principles/recheck_rules.md`. Working directory: the project root (PowerShell). Your brief gives the work file to check, your recheck number (1, 2…), your checklist file and your output file.

| Work | Checklist |
|---|---|
| Sector map (S5) | `s5r_sector_recheck.md` |
| Sector playbook (S7) | `s6_playbook.md` (S7R) |
| Gate, per batch (S8) | `s8r_gate_recheck.md` |
| Analysis (S13) | `s13r_analysis_recheck.md` |
| Allocation (S15) | `s15r_allocation_recheck.md` |

## How to check
1. Read the step file the work was done under (and everything it says to read), `/principles/recheck_rules.md`, your checklist file, then the work file.
2. **Recheck 2 or later:** start with what the previous recheck changed (its `recheck_log`) and anything it left `unresolved`, then go through the full checklist on the corrected work.
3. **Contrary evidence:** search against each claim the verdict rests on and log every search, as the recheck standard requires. Read `data/companies/<SYM>/search_log.json` first, so you don't repeat a search already done this quarter on the same documents.
4. Fix what is wrong. Where a conflict needs real judgement that you can't settle from the evidence, mark it `unresolved` with both sides and their sources: the orchestrator sends it to a deepest-tier subagent.
5. If a source fails, retry twice; if it's still unreachable or out of quota, stop and reply saying so.

## Output
Write the corrected work as your output file, in the same format as the work file (and, where the work has a plain-English `.md` summary, a corrected one beside it), with these added:
- `recheck_log`: one entry per change {item, old, new, evidence (document and page)};
- `contrary_search`: one entry per claim checked {claim, searched_for, where, found, result: "confirmed" / "contradicted" / "unresolved"};
- `unresolved`: conflicts needing a deepest-tier judgement {item, side_a, side_b, sources};
- `verdict_changed`: true if any decision, horizon, stage, marker, non-negotiable status, rank, proposed note or action changed;
- `learnings`: each gap the instructions, the fetch list or the rules should prevent next time {where: step file / checklist / `/workflow/fetch_learnings.md` / `/principles/investing_rules.md` sector note, what, evidence}. Don't edit those files yourself.
Downloads go into `data/companies/<SYM>/<FYyyQn>/` and are recorded in that company's `index.json` as `/principles/data_rules.md` describes.

Reply with: items checked, changes made (one line each), contrary searches (confirmed / contradicted / unresolved counts), verdict changed yes/no, learnings (one line each).

## For the orchestrator
- Run the rechecks `/principles/recheck_rules.md` allows, one after the other, each on the previous one's output.
- Tier: as in `/workflow/WORKFLOW.md`. Anything a recheck leaves `unresolved` goes to a deepest-tier subagent with both sides and their sources, before the next recheck.
- After each recheck, apply its learnings (fetch gaps into `/workflow/s12_fetch.md` or `/principles/data_rules.md`, sector notes into `/principles/investing_rules.md`, process gaps into the step or checklist file) before the next company; tell the user about those that alter an agreed outcome.
- Keep each company's contrary searches: append them to `data/companies/<SYM>/search_log.json` (date, quarter, step, claim, searched_for, where, found, result), so later rechecks and quarters see what was already looked for.
