@COMMON_AI.md

# Claude Code: project-specific items

**Precedence:** this file overrides the project's `COMMON_AI.md` (agent-specific over common); both override the user's global files.

- The screener login (`SCREENER_USERNAME`, `SCREENER_PASSWORD`) is in the user-level Claude env config; never read or print it.
- **Git:** besides what `COMMON_AI.md` lists, `CLAUDE.md` and `.claude/settings.json` are in git; `.claude/settings.local.json` is not.
- **Memory** (`~/.claude/projects/C--Users-sd391-Projects-Stock-Screener/memory/`) holds no instructions, only pointers to the project files; instructions go in the project files.
- The browser pane's MAX_MCP_OUTPUT_TOKENS is 3,000 tokens (`.claude/settings.local.json`, set at the user's request on 3 Nov 2026); see the browser-pane item in the global Claude file.
- WebFetch can't open nseindia.com or bseindia.com.
- Tiers map to models in the global Claude file; this project adds nothing to that mapping.
