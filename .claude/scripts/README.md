# scripts

`install-into-repo.sh [--src <dir|url>] [target]` is the only script. It
copies `skills/`, `scripts/`, `roles/` and `agents/` into `<target>/.claude/`
so Claude Code loads them as project skills (`/vk-implement`, ...), rewrites
every `/vk-` to `/vk-`, keeps `steward` under its bare name (a host looks for
`.claude/skills/steward/SKILL.md`; a foreign one there is left alone), stamps
`.claude/vk-version`, and leaves a self-copy at `.claude/vk-update.sh`. It never commits; it prints the `git` line to run.

Bash 3.2 (the macOS default) is the floor: no arrays, no `[[ ]]`, no GNU-only
flags, no `sed -i`. Tested by `tests/install.sh`.
