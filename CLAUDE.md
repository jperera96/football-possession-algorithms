# CLAUDE.md

Claude Code reads this file automatically. The canonical project policy is `AGENTS.md`, imported
below so Claude Code, Codex and humans follow one source of truth. Do not duplicate or override
its rules here.

@AGENTS.md

## Claude Code specifics

- OpenSpec workflows are installed as slash commands and skills under `.claude/`:
  `/opsx:explore`, `/opsx:propose`, `/opsx:new`, `/opsx:continue`, `/opsx:ff`, `/opsx:apply`,
  `/opsx:verify`, `/opsx:sync`, `/opsx:archive`, `/opsx:update`.
- `/opsx:propose`, `/opsx:new`, `/opsx:continue` and `/opsx:ff` produce **planning only**.
  Stop after them; a human must merge the specification PR before `/opsx:apply`.
- Before `/opsx:apply`, verify approval: `git fetch origin && git ls-tree -r --name-only origin/main openspec/changes/<id>/`.
  No output means not approved: do not implement.
- Check your work locally with:
  `python tools/governance/check_openspec.py --base origin/main --head HEAD --change <id>`
  (commit first; the checker compares revisions, not the working tree).
- `.claude/settings.json` denies reads of private competition assets. Never work around it
  (for example with `cat` in Bash).
- Generated files in `.claude/commands/opsx/` and `.claude/skills/openspec-*` come from
  OpenSpec 1.13.1; regenerate them only through an approved governance change
  (see docs/OPEN_SPEC_WORKFLOW.md, "Updating OpenSpec").
