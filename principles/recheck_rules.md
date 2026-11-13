# Recheck rules: what every recheck must meet

Judgement work is rechecked instead of being redone from scratch. This file holds the standards all rechecks share; how a recheck runs is in `/workflow/recheck.md`, and each step's own checklist in its recheck file.

## How many rechecks
| Work | How many rechecks |
|---|---|
| Sector map (S5) | 1; a 2nd only if the 1st changed a rank, stage or marker state |
| Sector playbook (S7) | 1; a 2nd only if the 1st changed a proposed note |
| Gate, per batch (S8) | 1; a 2nd only if the 1st changed a decision |
| Analysis (S13) | 2; a 3rd if the 2nd still changes the verdict |
| Allocation (S15) | 2; a 3rd if the 2nd still changes an action |

Why the gate and sector map get fewer: they are filters and orderings whose survivors get the full analysis and two rechecks in S13, so a second recheck adds something only when the first found a mistake. S13 and S15 produce the verdicts and actions the user acts on.

- **Cap:** if the last allowed recheck still changes a verdict, flag it to the user; never go past 3.

## Standards
- **Contrary evidence is the core of every recheck.** For each claim the verdict rests on, actively search for evidence against it (filings, transcripts, announcements, screener's figures, peers, official sector data). Log every search: what you looked for, where, and what you found. A search that finds nothing contrary is recorded as confirmation; a claim nobody searched against is not confirmed.
- **Evidence required:** screener.in (and BSE/NSE for what it lacks) is required. Never pass work on missing evidence.
