# Recheck: what every recheck shares

Judgement work is rechecked instead of being redone from scratch. This file holds what all rechecks share; each step's own checklist is in its recheck file:

| Work | Checklist | How many rechecks |
|---|---|---|
| Sector map (S5) | `process/s5r_sector_recheck.md` | 1; a 2nd only if the 1st changed a rank, stage or marker state |
| Sector playbook (S7) | `process/s6_playbook.md` ("S7R") | 1; a 2nd only if the 1st changed a proposed note |
| Gate, per batch (S8) | `process/s8r_gate_recheck.md` | 1; a 2nd only if the 1st changed a decision |
| Analysis (S13) | `process/s13r_analysis_recheck.md` | 2; a 3rd if the 2nd still changes the verdict |
| Allocation (S15) | `process/s15r_allocation_recheck.md` | 2; a 3rd if the 2nd still changes an action |

Why the gate and sector map get fewer: they are filters and orderings whose survivors get the full analysis and two rechecks in S13, so a second recheck adds something only when the first found a mistake. S13 and S15 produce the verdicts and actions the user acts on.

Working directory: the project root (PowerShell). Your brief gives the work file to check, your recheck number (1, 2…), your checklist file and your output file.

## How to check
1. Read the step file the work was done under (and everything it says to read), your checklist file, then the work file.
2. **Recheck 2 or later:** start with what the previous recheck changed (its `recheck_log`) and anything it left `unresolved`, then go through the full checklist on the corrected work.
3. **Contrary evidence is the core of every recheck.** For each claim the verdict rests on, actively search for evidence against it (filings, transcripts, announcements, screener's figures, peers, official sector data). Log every search: what you looked for, where, and what you found. A search that finds nothing contrary is recorded as confirmation; a claim nobody searched against is not confirmed. Read `data/companies/<SYM>/search_log.json` first, so you don't repeat a search already done this quarter on the same documents.
4. Fix what is wrong. Where a conflict needs real judgement that you can't settle from the evidence, mark it `unresolved` with both sides and their sources: the orchestrator sends it to a deepest-tier helper.
5. screener.in (and BSE/NSE for what it lacks) is required. If a source fails, retry twice; if it's still unreachable or out of quota, stop and reply saying so. Never pass work on missing evidence.

## Output
Write the corrected work as your output file, in the same format as the work file (and, where the work has a plain-English `.md` summary, a corrected one beside it), with these added:
- `recheck_log`: one entry per change {item, old, new, evidence (document and page)};
- `contrary_search`: one entry per claim checked {claim, searched_for, where, found, result: "confirmed" / "contradicted" / "unresolved"};
- `unresolved`: conflicts needing a deepest-tier judgement {item, side_a, side_b, sources};
- `verdict_changed`: true if any decision, horizon, stage, marker, non-negotiable status, rank, proposed note or action changed;
- `learnings`: each gap the instructions, the fetch list or the rules should prevent next time {where: step file / checklist / `process/fetch_learnings.md` / `process/investing_rules.md` sector note, what, evidence}. Don't edit those files yourself.
Downloads go into `data/companies/<SYM>/<FYyyQn>/` and are recorded in that company's `index.json` as `process/data_rules.md` describes.

Reply with: items checked, changes made (one line each), contrary searches (confirmed / contradicted / unresolved counts), verdict changed yes/no, learnings (one line each).

## For the orchestrator
- Run the rechecks in the table above, one after the other, each on the previous one's output. If the last allowed recheck still changes a verdict, flag it to the user; never go past 3.
- Tier: as in `process/README.md`. Anything a recheck leaves `unresolved` goes to a deepest-tier helper with both sides and their sources, before the next recheck.
- After each recheck, apply its learnings (fetch gaps into `process/s12_fetch.md` or `process/data_rules.md`, sector notes into `process/investing_rules.md`, process gaps into the step or checklist file) before the next company; tell the user about those that alter an agreed outcome.
- Keep each company's contrary searches: append them to `data/companies/<SYM>/search_log.json` (date, quarter, step, claim, searched_for, where, found, result), so later rechecks and quarters see what was already looked for.
