@COMMON_AI.md

# Claude Code: project-specific items

**Precedence:** this file overrides the project's `/COMMON_AI.md` (agent-specific over common); both override the user's global files (`~/.common-ai/COMMON_AI.md`, `~/.claude/CLAUDE.md`).

## Project map
- **Start here (orchestrator manual):** `/workflow/orchestrator.md`
- **Principles index:** `/principles/PRINCIPLES.md`
- **Workflow index:** `/workflow/WORKFLOW.md`
- **Sources index:** `/sources/SOURCES.md`
- **Scripts index:** `/scripts/SCRIPTS.md`
- **State folders:** `data/`, `runs/`, `archive/` (`/COMMON_AI.md`)

## Claude-only items
- The screener login (`SCREENER_USERNAME`, `SCREENER_PASSWORD`) is in the user-level Claude env config; never read or print it.
- **Git:** besides what `/principles/PRINCIPLES.md` lists, `CLAUDE.md` and `.claude/settings.json` are in git; `.claude/settings.local.json` is not.
- **Memory** (`~/.claude/projects/C--Users-sd391-Projects-Stock-Screener/memory/`) holds no instructions, only pointers to the project files; instructions go in the project files.
- Tiers map to models in `~/.claude/CLAUDE.md`; this project adds nothing to that mapping.
