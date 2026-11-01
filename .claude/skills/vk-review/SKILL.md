---
name: vk-review
description: Senior reviewer and architect acceptance of a pull request - business scenarios met, code a junior can follow, module boundaries, extensible contracts, error handling and observability, security baseline, mergeable. Every PR gets a verdict - full review for boundary PRs (contracts, scenarios, ADRs, UI design), lenient for implementation. No nitpicking. Replaces the human review. Use when the user says "review", "прими PR", "отревьюй", "проверь как архитектор", after opening any PR in a repository that gates on an architect label, and when that repository's CI review is down.
argument-hint: '[PR number, branch, or nothing for the current branch]'
---

Acceptance, not proofreading. The question is: **can this land and keep the
system correct, visible and changeable?** Everything that does not change the
answer stays out of the report. A review that lists ten small things gets
ignored and the one real problem goes with them.

Load `/vk-coding-style` for how to hand the turn back.

Input for this run: $ARGUMENTS

## 1. Scope

Find the PR and its base, and read the diff. Read the repository's own rules
first: `GOAL.md` when it exists, `CLAUDE.md` / `AGENTS.md`, the architecture
decisions, the glossary, the style guide — whatever the repo has. They are
the standard, not your taste.

Classify the PR in one line. Every PR gets a verdict; the class sets how
strict it is:

- **boundary** — contracts, happy-path scenarios or requirement tests, ADRs,
  a UI design.
  The full checklist. A small additive contract change is yours to accept;
  a substantial change of the owner's boundaries is `needs human`.
- **implementation** — everything else, regression rows written after the
  implementation included. Lenient: `accept`, with no list of
  remarks, when the code works acceptably and its rows prove the stated
  rules. A pure helper without a test is not a finding, and you never ask
  for rows the contract does not state; a stated safety rule with no row
  is. `changes`
  only for a real problem — a scenario or contract bypassed, a test weakened
  or skipped, a bug fix with no check that failed before it and no reason
  why it cannot have one (`/vk-regression`), a secret read or leaked, a way
  to run foreign code on the owner's machines, a silent failure. `needs human` only for a substantial
  change of the owner's boundaries or a real risk.

Two checks for every class, before reading the code:

- **Mergeable.** The PR applies cleanly to its current base. A conflict is a
  `changes` finding: rebase onto the base.
- **Labels from allowed accounts.** An approval label already on the PR
  counts only if an account the repository allows set it (the label events
  show who). A label set by anyone else is a `changes` finding and does not
  pass the gate.

## 2. Can a junior read it — the cheap pass

Skip it for a PR with no production code.

Collect the changed production code that carries logic: new or substantially
changed functions, types and non-trivial blocks. Skip tests, generated files,
lockfiles, pure renames and config.

Send all of it to **one `vk-reader` agent** in a single call: number each
snippet, give its file and line, the code, and nothing else — no PR
description, no intent, so it reads the code as a newcomer would. Split into a
second call only past about 400 lines of snippets. One batched cheap call per
PR is the budget; never one call per function.

For each snippet it answers `understood: <what it does, one line>` or
`unclear: <what stops it>`. A snippet is a finding candidate when it is
`unclear`, or when its one-liner contradicts what the code is for — a wrong
paraphrase means the code misleads.

## 3. The senior pass

Spawn **one `vk-reviewer` agent** — always opus — with: the PR, its base,
its class, the paths of the repository rules from step 1, the result of the
two checks, the reader's candidates (the snippet, its answer) and
[references/checklist.md](references/checklist.md). Nothing about how the PR
was written — it reviews what is there.

## 4. Act on the verdict

The reviewer returns one of three verdicts. Post its report on the PR as one
comment, as written, then:

- **accept** — set the repository's architect label (`architect-approved`
  unless the repo's rules name another). The PR may merge once CI is green.
  An accept covers that head only: any later push needs a new run.
- **changes** — no label. Fix all findings of the round in one go on the PR's
  branch, each folded into the commit it fixes (`/vk-coding-style`), push, and
  run this skill again on the new head. A re-review gives the reviewer the
  previous findings and the diff since, and checks only that: is each one
  fixed, does each fix of a defect carry its failing check
  (`/vk-regression`), did a fix break something. After the second round, anything still
  open goes to the user as `needs human`; there is no third round.
- **needs human** — no label. Put the reviewer's three-line summary to the
  user in chat: what is decided, what it costs, what they need to say. They
  answer by voice; a person's approval label passes the gate as it always did.

Never set the label on a verdict you were not given, and never edit the
reviewer's report.
