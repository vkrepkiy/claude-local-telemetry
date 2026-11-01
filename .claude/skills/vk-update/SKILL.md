---
name: vk-update
description: Refresh this repo's installed vk skills to the latest version and report what changed. Use when the user says "update the skills", "refresh vk", "обнови скиллы", "are my skills current", or asks whether they're behind on vk. Safe to fire on its own — everything it touches is files in this repo, undone by `git checkout`.
argument-hint: '[--src <dir|url>]'
allowed-tools: ["Bash(.claude/vk-update.sh:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/install-into-repo.sh:*)"]
---

If `.claude/vk-version` exists at the repo root, read it first and keep the
line — that is the *old* version, sha and date (or `pending ...` if a
previous install was interrupted and never finished).

Then re-run the installer:

- If `.claude/vk-update.sh` exists at the repo root, this repo already has a
  repo-local install of vk — run `.claude/vk-update.sh $ARGUMENTS`. It is a
  self-copy of the installer: it clones the latest commit of the source repo
  (or whatever `--src <dir|url>` names) and reinstalls from that, same as a
  first install.
- Otherwise this skill is running as the `vk` plugin itself, not a
  repo-local copy — run `${CLAUDE_PLUGIN_ROOT}/scripts/install-into-repo.sh
  $ARGUMENTS` against the current repo instead.

Either script wipes and reinstalls `skills/`, `scripts/`, `roles/` and
`agents/` under `.claude/`, rewrites every `/vk-` handoff to `/vk-`, and
re-stamps `.claude/vk-version`. It never commits — it only prints the git
command to run. Running it twice with nothing new upstream changes nothing.

Read the script's output and report in a few lines:

- the old version line (from the read above, or "no `.claude/vk-version` —
  first install")
- the new `INSTALLED: ...` line
- the `git add ... && git commit ...` line it printed, verbatim, so the user
  can run it themselves
- one line: skills load at session start, so a new session is needed before
  the updated ones are live.

Do not run the commit command yourself — the script prints it, it does not
execute it, and neither should you. If the script printed an
`INSTALL_ERROR(...)` line instead, report that error and stop rather than
retrying with different arguments on your own guess.
