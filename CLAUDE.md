@COMMON_AI.md

# Claude Code: project-specific items

- **Screener login:** the user-level environment configuration that `/sources/screener.md` names is this project's environment variables, set in the Claude desktop app (stored by the app, not in a project file); every shell the app opens for the project has them.
- **Git:** besides what `/principles/PRINCIPLES.md` lists, `CLAUDE.md` and `.claude/settings.json` are in git; `.claude/settings.local.json` is not.
- **Memory** (`~/.claude/projects/C--Users-sd391-Projects-Stock-Screener/memory/`) holds no instructions, only pointers to the project files; instructions go in the project files.
