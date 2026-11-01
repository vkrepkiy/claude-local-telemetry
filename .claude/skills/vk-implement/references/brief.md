# Module brief (template)

Fill the angle brackets and send this as the spawn prompt. Keep it this
short: the brief carries the goal and the limits, the agent decides the how.

---

Make the module `<module>` pass its scenarios. Nothing else.

Read first: the repository's `CLAUDE.md` / `AGENTS.md` and style docs, then
the contract `<contract path>` — every doc comment is a requirement — then
the scenarios `<scenarios path>`<, and the approved design <link or path>>.

Work on branch `<branch>` from a fresh `<base>`. Touch only `<module path>`
(plus the lockfile through the package manager). Never change the contract,
the scenarios or the design; never weaken, skip or silence a test, a type or
a lint rule. Run `<the module's check command>` until it is green, then the
repository's full check.

`<External adapter only:>` pass subprocesses and SDKs only the environment
variables they need, never log secrets, give models no acting tools by
default.

If the contract is not enough to decide something, do not invent it in
code and do not stop: open a contract PR `contract/<module>-<what>` (only
contracts and scenarios, saying additive or breaking and why), stack your
branch on it, carry on, and drive that PR per `/steward`. It lands right
before your module.

Commit per `/vk-coding-style`, push the branch, do not open the module PR.
Reply with exactly these six lines:

```
pushed: yes|no <branch> <commit sha>
check runs until green: <n>
failures on the way: <one line>
implemented without a scenario: <list or "none">
cannot pass inside the contract: <scenario — why, or "none">
contract PRs: <links or "none">
```

"implemented without a scenario" is the main detector of holes in the
scenarios — read it every time. "cannot pass inside the contract" is the
first run of the scenarios against real code: a line there is a scenario
to fix, never a test to weaken.
