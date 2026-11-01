---
name: vk-regression
description: Turn every defect found into a check that fails while the defect is there, so the same mistake cannot come back unnoticed - red first, then the fix. A defect is behaviour that is wrong against what was intended - a bug in code or a script, two parts that disagree on a file or a field, a broken repository rule, a wrong assumption in a plan or a requirement. Use whenever one is found or reported - by CI, a review finding, a crash, a manual run, or the user ("баг", "сломалось", "не работает", "почему падает", "опять то же самое", "fix the bug", "it broke again") - before fixing it, and when the user says "regression test", "регрессионный тест", "покрой тестом", "чтобы не повторилось". Not for new features, wording or typos in prose, or a flaky runner or an outage outside the repository.
argument-hint: '[the defect, or nothing to take it from the conversation]'
---

A defect that was found is proof the checks have a hole. The fix closes it
once; a check that fails while the defect is there closes it for good. The
order is the point: **red first, then the fix.**

Input for this run: $ARGUMENTS

## 1. State it

One line: in what situation, what happened, what should have happened. If you
cannot say what should have happened, ask the user — that question is the
defect.

Already caught by a check that went red? That check is the regression; go to
step 4.

## 2. Find the check

The cheapest check that fails exactly when this defect is present, at the
level where it shows:

- **a bug in code or a script** — a test through its public interface: the
  function, the command line, the contract; never the internals;
- **two parts that disagree** (a field name, a file one writes and the other
  reads, seconds against frames) — one end-to-end test that runs the producer
  and feeds its real output to the consumer;
- **a broken repository rule** — an assertion in the repository's own checks,
  the way `MUST_STAY_GATED` guards the gating rule here;
- **a wrong assumption in a plan or a requirement** — a requirement test or a
  scenario that states the corrected one, as `/vk-implement` writes them.

Use the repository's test runner and layout. Code with no tests at all gets
the smallest harness its language uses, wired into CI — that is part of the
fix, not extra scope. One behaviour per test, input to output, no sleeps; a
flaky or brittle check is worse than none.

Cannot be checked automatically — it needs a paid desktop app, a human
judgement of picture or sound, a third party: try a fake for that part first.
Still not checkable: say so in one line with the reason, and write the manual
check into the PR description.

Before adding a test, look for the one that should have caught it — a
scenario, a table of cases, a test of the same command. Add a case there or
fix that test; a new test only when nothing nearby fits. A defect that would
not hurt anyone if it came back gets no check at all.

Name the test after the behaviour it guards, not the incident:
`hook check accepts two hooks`, not `bug 42`. The name is what lets someone
decide later whether it still matters.

## 3. See it fail

Run the check on the code as it is. It must fail, and fail for this defect: the
message names the wrong behaviour, not an import error, a missing fixture or a
typo in the test. A check that passes before the fix tests something else —
rewrite it. Keep the failing output.

## 4. Fix it, see it pass

Fix the cause, not the symptom the check looks at. The new check and the whole
suite pass. Where the same mistake obviously repeats — a sibling script, the
same pattern next door — cover it in the same check; no hunt across the code
base.

## 5. Land it

The check and its fix go in one commit, `fix(<scope>): …`, per
`/vk-coding-style`: with rebase-merge every commit lands on `main`, and a red
commit there breaks bisect. Several defects, one commit each. The PR
description shows the red run and the green one.

A fix with neither a check that failed first nor a one-line reason it cannot
have one is not done — `/vk-review` returns `changes`.

## When a regression check goes

A check guards a behaviour, not a memory of a bug. Delete it, without
ceremony, in the change that makes it pointless:

- **the behaviour is gone or no longer wanted** — the feature, the command,
  the field, the requirement was removed or replaced;
- **another check covers it** — two tests that would fail for the same
  reason, keep the one closer to the user;
- **it is flaky or tests internals** — rewrite it through the public
  interface; if that cannot be done, delete it and say what is now unguarded.

The PR says in one line per deleted check which of these it is. `/vk-review`
is the judge: deleting a check whose behaviour still exists is a test
weakened, `changes`; keeping one whose behaviour is gone is dead code, and the
architect may ask for it to go. Never skip or disable a check instead of
deciding.
