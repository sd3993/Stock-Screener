# Recheck: what every recheck shares

Judgement work is rechecked instead of being redone from scratch. This file holds what all rechecks share; each phase's own checklist is in its recheck file:

| Work | Checklist | How many rechecks |
|---|---|---|
| Gate, per batch (F4) | `process/future/f4r_gate_recheck.md` | 1; a 2nd only if the 1st changed a decision |
| Sector map (F5) | `process/future/f5r_sector_recheck.md` | 1; a 2nd only if the 1st changed a tier |
| Analysis (F8) | `process/future/f8r_analysis_recheck.md` | 2; a 3rd if the 2nd still changes the verdict |
| Allocation (F10) | `process/future/f10r_allocation_recheck.md` | 2; a 3rd if the 2nd still changes an action |

Why the gate and sector map get fewer: they are filters and orderings whose survivors get the full analysis and two rechecks in F8, so a second recheck adds something only when the first found a mistake. F8 and F10 produce the verdicts and actions the user acts on.

 Working directory: the project root (PowerShell). Your brief gives the work file to check, your recheck number (1, 2…), your checklist file and your output file.

## How to check
1. Read the phase file the work was done under (and everything it says to read), your checklist file, then the work file.
2. **Recheck 2 or later:** start with what the previous recheck changed (its `recheck_log`) and anything it left `unresolved`, then go through the full checklist on the corrected work.
3. **Contrary evidence is the core of every recheck.** For each claim the verdict rests on, actively search for evidence against it (filings, transcripts, announcements, screener's and Tapetide's figures, peers). Log every search: what you looked for, where, and what you found. A search that finds nothing contrary is recorded as confirmation; a claim nobody searched against is not confirmed. Read `data/companies/<SYM>/search_log.json` first, so you don't repeat a search already done this quarter on the same documents.
4. Fix what is wrong. Where a conflict needs real judgement that you can't settle from the evidence, mark it `unresolved` with both sides and their sources: the orchestrator sends it to an Opus high helper.
5. screener.in (and Tapetide and BSE/NSE for what it lacks) is required. If a source fails, retry twice; if it's still unreachable or out of quota, stop and reply saying so. Never pass work on missing evidence.

## Output
Write the corrected work as your output file, in the same format as the work file (and, where the work has a plain-English `.md` summary, a corrected one beside it), with these added:
- `recheck_log`: one entry per change {item, old, new, evidence (document and page)};
- `contrary_search`: one entry per claim checked {claim, searched_for, where, found, result: "confirmed" / "contradicted" / "unresolved"};
- `unresolved`: conflicts needing an Opus high judgement {item, side_a, side_b, sources};
- `verdict_changed`: true if any decision, eligibility, non-negotiable status, tier or action changed;
- `learnings`: each gap the instructions, the fetch list or the rules should prevent next time {where: phase file / checklist / `process/fetch_learnings.md` / `process/investing_rules.md` sector note, what, evidence}. Don't edit those files yourself.
Downloads go into `data/companies/<SYM>/<FYyyQn>/` and are recorded in that company's `index.json` as `process/data_rules.md` describes.

Reply with: items checked, changes made (one line each), contrary searches (confirmed / contradicted / unresolved counts), verdict changed yes/no, learnings (one line each).

## For the orchestrator
- Run the rechecks in the table above, one after the other, each on the previous one's output. If the last allowed recheck still changes a verdict, flag it to the user (`acknowledgements.md`); never go past 3.
- Model: as in `process/future/README.md`. Anything a recheck leaves `unresolved` goes to an Opus high helper with both sides and their sources, before the next recheck.
- After each recheck, apply its learnings (fetch gaps into `process/future/f7_fetch.md` or `process/data_rules.md`, sector notes into `process/investing_rules.md`, process gaps into the phase or checklist file) before the next company; those that can alter outcomes go in `acknowledgements.md` (`CLAUDE.md`, "Updates from learnings").
- Keep each company's contrary searches: append them to `data/companies/<SYM>/search_log.json` (date, quarter, phase, claim, searched_for, where, found, result), so later rechecks and quarters see what was already looked for.
