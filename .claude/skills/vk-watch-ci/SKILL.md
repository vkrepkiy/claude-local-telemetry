---
name: vk-watch-ci
description: After a git push or PR merge, watch the GitHub Actions run it triggers until it finishes, and if it fails, diagnose the failure from the logs, fix it, push the fix, and watch again — looping until green or genuinely blocked. Use right after pushing commits, right after merging a pull request, or when the user says "watch CI", "watch the pipeline", "make sure the pipeline passes", "fix the build". GitHub Actions only — this repo has no GitLab pipeline.
argument-hint: '[optional: PR number, branch, or run id — defaults to the current branch/PR]'
---

Fire this on yourself, not just on request: any time a push or merge just happened and it could have started a workflow run, watch it through instead of walking away.

> **Other hosts:** Use the host's available GitHub integration or `gh`. Ignore Claude-only `mcp__ccd_pr__*` tool names below when they are unavailable, while preserving the same watch, diagnose, fix, push, and recheck loop.

Load `/vk-coding-style` for how to hand the turn back.

## 1. Does this push/merge actually trigger a run?

Check the workflow triggers (e.g. `.github/workflows/*.yml`, `on:` blocks) against what just happened — a push to a branch with no open PR and no `push:` trigger on that branch starts nothing, so there is nothing to watch. A push to `main`, a push to a branch with an open PR, or any merge into a watched branch counts — go to step 2. When unsure, check anyway rather than silently skipping it.

## 2. Watch the run

Prefer the harness's built-in PR tools over polling `gh` by hand:

- If this session already has a PR bound (or one exists for the branch), use `mcp__ccd_pr__bind_pr` (if not yet bound), then `mcp__ccd_pr__set_monitor` and `mcp__ccd_pr__get_status` to follow it through to completion.
- No bound PR / no PR at all (e.g. a push straight to `main`): use `gh run watch` (or `gh run list --branch <branch> --limit 1` to find the run id first, then `gh run watch <id> --exit-status`).

Either way, wait for a real terminal result — pass or fail. Don't guess from "it's probably fine."

## 3. On failure

1. Pull the failing job's logs: `gh run view <run-id> --log-failed` (or the ccd_pr status detail if that's what you're using).
2. Read the actual error, not just the job name. Find the root cause in the diff that caused it.
3. **Judge the fix before making it:**
   - **Small and obvious** — typo, lint/format, a missing import, an off-by-one, a version pin, a flaky-test retry, anything you can point at the exact line and be sure of the fix: just fix it, no need to ask.
   - **Big, risky, or genuinely unsure** — the fix touches logic/behavior beyond the failing line, changes a public interface or config a user depends on, deletes/rewrites a test rather than fixing the code under it, or you're guessing rather than sure: stop, show the user the failure and your proposed fix, and wait for a go-ahead before touching anything.
   - When in doubt, treat it as the risky case — ask.
   - A red test that caught a real defect already is the regression check — fix the code. A defect no check caught (it broke a deploy step, a script, a build) gets one first, per `/vk-regression`.
4. Fix it per `/vk-coding-style`: on your own unmerged branch fold the fix into the commit it fixes and push with `--force-with-lease`; on `main` or someone else's branch add a new commit. Never `--no-verify`, never plain `--force`.
5. Push the fix, then go back to step 2 and watch again.

Cap it at **3 fix attempts** for the same run. If it's still red after that, stop and report the failure plainly to the user instead of continuing to loop — a fourth guess is more likely to be flailing than fixing.

Stop and ask immediately, without spending an attempt, when the failure isn't something a code change can fix: a missing secret/credential, a flaky/infra error unrelated to the diff, or anything that needs an approval or access change outside the repo.

## Boundaries

- Never enable auto-merge — that stays an explicit ask, regardless of CI status.
- Never plain `--force`, skip hooks, or disable a failing check to make the pipeline look green.
- This loop covers *fixing the code so CI passes*. It is not permission to change what CI checks, weaken a test, or merge over a real failure.
