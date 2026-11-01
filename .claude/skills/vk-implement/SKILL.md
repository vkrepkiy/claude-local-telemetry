---
name: vk-implement
description: Build a feature or module contract-first - decompose it, agree the boundaries with the user (contracts, UI design, happy-path input/output tests), then hand the coding to subagents who have full freedom inside those boundaries; edge cases come later, one per defect found. Use when the user says "implement", "let's build it", "start coding", "run the implementation", "реализуй", "запусти реализацию", "давай кодить".
argument-hint: '[what to build, or nothing to continue from the conversation]'
---

The human owns the boundaries; agents own everything inside them. All the
thinking and all the decisions happen before code, and the human reviews
exactly three kinds of thing: **contracts, the UI design, the happy-path
tests**. After that nobody reviews the implementation line by line — the
approved tests passing inside the approved contracts is the acceptance, and
the architect review of each implementation PR checks it was not bypassed
and finds the rule the rows missed. Agents call the human
only for a substantial change of a boundary or a real risk.

Load `/vk-coding-style` for names, commits, when to push, and how to hand the turn back.

Input for this run: $ARGUMENTS

## 0. Start from what already exists

Read the conversation, any consult notes, and the repository: contracts,
interfaces, tests, design links, `docs/modules.md`, `backlog.md`. When the
tree in `docs/modules.md` exists, work on one node of it — the one named, or
the next open line of `backlog.md` — inside its approved contract. Every stage below whose result
already exists **and was approved** is skipped. Say in one line which stage
you are starting at. Before decomposing a node that is not a line of `## Now`
or `## Next`, run `/vk-compass` and show its verdict.

## 1. Decompose

Split the work into modules, each a small self-contained program with a clear
input and output, simple enough that an agent can make its tests pass without
design decisions. Show the modules and the arrows between them — nothing more
— what can be built in parallel, and the order they land in: earliest first
whatever gives the owner something to click or try, as in `/vk-split` step 2. A module is a capability or a unit with
behaviour, never an entity or a table — those live in the schema and the
contracts.

No fanaticism: split until each piece is simple enough for an agent, and stop
there. An extra layer of contracts is as much debt as a missing one. A small
change is one module; say so and move on.

**Too big for one pass** — more than five or six modules, several independent
end-to-end paths, a done-condition made of unrelated items, or a module you
cannot describe without its own design decisions: stop and run `/vk-split`
on it. It splits, researches the children with real unknowns, and gets one shared contract
approved; then come back here once per child. This applies at any depth — a
module found too big mid-build is split the same way.

## 2. Contracts — gate

When the node has a UI people use, pass step 3 first: the contracts start
from the approved screens, and a mock behind the contract keeps the screens
clickable until the real backend lands. Without UI, start here.

For every arrow: the types, and a doc comment on every member stating its
behaviour. Start from the consumer, not the internals: show usage examples
from the simplest case to the awkward ones, and ask "would I want to use
this?". Shape them per [references/contracts.md](references/contracts.md).
Iterate with the user until they approve.

For a risky module — it moves money or credits, deletes data, or holds a
state machine several modules touch — offer `/vk-consult critic architect`
on its contract before asking for the "ok". Skip it for plain modules.

In an app (Flutter, Kotlin, …) the contract is the pure core layer: declare
its interfaces first, a doc comment on every member and a body that only
throws (`throw UnimplementedError()` or the language's equivalent).

## 3. UI design — gate, only when there is UI

No UI code before the design is approved. Prototype it in Claude Design, or
ask the user to, and get at least a screenshot or a link approved. That design
is the source of truth for how it looks and feels; the contract and tests
cover what it does.

## 4. Happy-path tests — gate

The happy path through each public entry of the contracts, per
[references/testing.md](references/testing.md) — in an app, requirement
tests against the core layer in its protected `test/requirements/` folder.
One **`vk-tester`** agent per module, in parallel, with the brief from
[references/test-brief.md](references/test-brief.md) and a context pack built
as in `/vk-split` step 3: the module's contract files, `testing.md`, and one
existing test file of the repository as the layout to follow. Corner cases
wait for step 6; passability is proven in step 5. The user reviews the
scenarios.

**How a gate is passed.** In cloud mode, contracts, tests and the design link
go into one pull request, and `/vk-review` accepts it: its `accept` passes the
gate, its `needs human` waits for the user. In local mode, show them in chat
and wait for an explicit "ok". Never start step 5 on an unapproved boundary.

## 5. Implement — no gates

One subagent per module, in parallel where modules do not depend on each
other, each on its own branch or worktree, started from a freshly updated
base. Spawn each as the **`vk-module`** agent and write its brief yourself
from [references/brief.md](references/brief.md): what the module is, where its
contract, scenarios and design are, what it must not touch. Do not tell it
*how* — the brief carries goals and limits, never steps.

The implementation proves the scenarios passable: one the agent reports it
cannot pass inside the contract, you fix in a contract PR, as below, and
stack the module branch on it.

**A missing contract never stops an agent.** It opens a separate contract
PR (`contract/<module>-<what>`: only contracts and scenarios, saying additive
or breaking and why), stacks its module branch on it and carries on. It never
works around the contract in code. `/vk-review` accepts a small additive
change; a substantial one goes to the user. The contract PR and its
implementation land as a pair, one right after the other.

## 6. Edge cases — only on request

There is no edge-case pass by default: a module whose happy-path rows are
green goes straight to step 7, and its edge cases arrive one at a time, each
behind a defect a review, a smoke run or a live bug found, red first per
`/vk-regression`. Run the pass only when the user asks for it, or for a
module whose whole job is unhappy input (a parser, a protocol adapter): then
one more **`vk-tester`** — never the agent that implemented it, so the code
does not grade itself — adds the rows to the module's branch, per
`testing.md`, with the step 4 pack plus the module's path and the
implementer's report. A red row is a bug: a `vk-module` with the module's
brief fixes it — the row is the red check, the fix is folded into the row's
commit, the row stays as written. What the tester reports the contract
leaves open, you settle in a contract PR, as in step 5.

## 7. Integrate and land

Run the repository's full check. Every module PR goes through
`/vk-review`: lenient for implementation, it accepts when the code works and
its rows prove the stated rules, and looks for the signs of a
bypass — contracts or tests changed by an implementer, tests weakened or
skipped, type or lint suppressions, files outside the module. The agent that opened a PR drives it to merged per
`/steward`. A module that failed is not repaired — start a fresh agent
with the same brief.

Land it per `/vk-coding-style`: cloud mode ends in an open PR; local mode
reports and waits. Anything real but out of scope goes to `backlog.md`.

## When a bug shows up live

A live bug means a wrong test or a blind spot. Find which scenario should
have caught it and fix or remove wrong ones; then `/vk-regression`: an
end-to-end regression of the live case, watched **failing on `main`**, then
the fix.
