---
name: steward
description: Drive a pull request you opened to merged - stay subscribed, act on every red check, review verdict and comment, run the review yourself when the CI review is down, rebase stacked children after their base merges, and call the owner only once, in one line. Use right after opening a pull request, when PR activity arrives, and when the user says "drive the PR", "доведи PR", "babysit the PR", "why is the PR stuck".
argument-hint: '[PR number or branch, or nothing for the PR of the current branch]'
---

No PR hangs. The agent that opened a PR owns it until it is merged, or until
the owner closes it. Opening the PR is not the end of the task; the merge is.

Claude Code cloud sessions look for `.claude/skills/steward/SKILL.md` in the
repository when they drive a PR, so this skill keeps the name `steward`.

Load `/vk-coding-style` for how to hand the turn back.

Input for this run: $ARGUMENTS

## Stay on it

- Subscribe to the PR's activity (Claude Code cloud: subscribe to PR
  activity; elsewhere watch it with `gh`). Stay subscribed until it merges.
- **A red check:** fix it per `/vk-watch-ci`.
- **A review verdict or comment:** `changes` — fix all findings of the round in
  one go, fold each fix into the commit it fixes, push; review rounds are
  capped as in `/vk-review`. A finding that is a defect gets its
  failing check first, per `/vk-regression`. `accept` — it merges by the
  repository's rules (a review workflow merges it, or you rebase-merge it if
  the rules let the agent). `needs human` — see "Calling the owner".
- **The CI review is down** — no run on the new head, the run errored, or no
  verdict after the run finished: run `/vk-review` in this session and act on
  its verdict the same way.
- **A conflict with the base:** rebase onto it, resolve, push. A conflict is a
  `changes` finding, never a reason to wait.

## Stacked PRs

A contract PR (`contract/<module>-<what>`) and the implementation stacked on
it land as a pair, one right after the other. When a base PR merges, rebase
each child onto `main`, point its PR at `main`, push, and keep driving it.

## History

Push your own branches with `--force-with-lease`; that is always allowed
there. Before overwriting a remote branch, fetch deep enough and check that
its commits you are about to drop are already in `main` (compare by subject:
a rebase-merge changes the SHAs).

## Calling the owner

Only for a substantial change of the owner's boundaries, a real risk, or
findings still open after the second review round. Say
it once, in one place, in one line: what is needed and what to answer. Then
carry on with everything that does not wait on it. Never repeat the call on
every event.

## Done

The PR is merged: update `main`, rebase any children, and carry on with the
task that opened it. Never merge over a red check, never set an approval
label without a verdict that gives it, never disable a check to get green.
