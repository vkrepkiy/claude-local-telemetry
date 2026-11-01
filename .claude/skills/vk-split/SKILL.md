---
name: vk-split
description: Split something too big to build in one pass - a product, a stage, a module - into child modules, research each child with real unknowns in parallel, and reconcile the findings into one shared contract for the user to approve. Works at any level, from discussion or from inside /vk-implement. Use when the user says "split", "break it down", "the project is big", "let's agree on modules", "разбей", "проект большой", "давай договоримся о модулях", or when /vk-implement finds a node too big.
argument-hint: '[the node to split, or nothing to take it from the conversation]'
---

One loop for any **node** — a product, a stage, a module. A node is a
**leaf** when one agent can make its tests pass without design decisions; a
leaf goes to `/vk-implement`. Anything bigger is split here, and every child
goes through the same loop again. Discussion and implementation are the same
loop at different depths.

Load `/vk-coding-style` for names, commits, when to push, and how to hand the turn back.

Input for this run: $ARGUMENTS

## 0. Find the node

From the input, the conversation and `docs/modules.md` (the tree, if the
repository has one). Read the parent's approved contract if there is one —
the node must fit it. Read the requirements the node answers to.

Before splitting a node that is not a line of `## Now` or `## Next` in
`backlog.md`, run `/vk-compass` and show its verdict.

If it is already a leaf, say so in one line and hand it to `/vk-implement`.
Signals it is not: more than five or six modules, several independent
end-to-end paths, a done-condition made of unrelated items, data owned by
more than one part.

## 1. Choose the axis

Every split answers one question — what are the children *of*. The level of
the node decides it:

| node | split by | children | example |
| --- | --- | --- | --- |
| product, system — the root, or an empty repo | what deploys and where its code lives | deployable apps, shared packages, infra in its own folder | `apps/web`, `apps/api`, `packages/database`, `infra/` |
| one deployable app or package | capability: a set of rules with its own data and invariants | bounded contexts | `auth`, `deal-workflow`, `ledger` |
| one capability | units, one input → output each | leaves for `/vk-implement` | `close-deal`, `post-transfer` |

A stage — an MVP, a release — is not a level: it narrows the requirements,
and the axis comes from where its code lands. "Разбей MVP" in an empty repo
is a system split.

Use the axis the user named. Otherwise take it from the table and say it in
the first line of the proposal. Ask only when the level is unclear — the
node could be a new deployable or a capability of an existing one — and then
in one line: the two axes, one example child each.

Never:

- **entities or tables as modules** — users, deals, credits are the database
  schema and the contracts; a module owns data, it is not data;
- **a name that says nothing** — `platform`, `core`, `common`, `misc`: if
  it cannot be named by what it deploys or what it decides, it is not a child;
- **infra or deploy inside a code module** — it is its own child at the
  system level;
- **two axes in one split** — an app next to a capability next to an entity.

## 2. Split — gate

Propose, along that axis, the children, the arrows between them, the data
each one owns, and the order they land in. Name what can be built in
parallel.

**Landing order: something a human can touch, early.** Pull a thin vertical
slice forward — app shell and the first screen on a mock backend — instead
of finishing every shared package first; a shared package lands only as far
as that slice needs it. For each child, say whether the owner can click or
try something after it lands, or after which child they first can. For a
**human-first** product (a UI people use): approved UI design → a clickable
slice of the real app on a mock → the API contract shaped by what those
screens need → backend. A service, library or backend with no human UI
stays contract-first. No throwaway demos, no skipped gates.

Mark each child `research` — real unknowns remain at its boundary — or
`derive` — the approved parent contract already fixes its contract, as for
screens over a fixed API. Nothing more: no contracts yet.

When the split creates repository structure, show the folder layout as a
tree. At the system level also name a stack hint per child (framework,
hosting, monorepo tool) — from the requirements or the user, marked a hint:
research confirms or challenges it.

Who approves:

- **The user** when the node is the top of the tree or the split would change
  the parent's contract. Wait for an explicit "ok".
- **Nobody** when the node sits inside an approved parent and the split
  changes nothing at its boundary: show it in one message and carry on.

Split until each child is simple enough, and stop. An extra layer of
contracts is as much debt as a missing one. Default ceiling: six children per
split; group screens per deployable unless one group is clearly more than one
agent's work.

## 3. Context pack, then research — one agent per `research` child, in parallel

Only `research` children are researched; a `derive` child skips this step and
the integrator drafts its contract directly.

First the lead names, per `research` child, the routes and types, the
requirement sections and the design screens it touches (it read the
requirements in step 0). Then one **`vk-errand`** agent writes, per
`research` child, a pack file in a scratch directory outside the repository
tree: exactly those, excerpted, each with `path:line`, under a list of what it
was asked for. The errand copies, it does not judge.

Then all research calls in one message, each as the **`vk-research`** agent,
with the brief from [references/research-brief.md](references/research-brief.md):
the child, the axis, its neighbours and arrows, its stack hint, its pack, the
parent contract and the scratch path for its note. Each writes what its child
needs and offers — not how to build it.

## 4. Reconcile

First read the open questions of the notes and decide every one where the
simplest option is obvious. Only a product, irreversible or cost/risk
question goes to the user — once, as one numbered list; their answers join
the decisions.

One **`vk-integrator`** agent gets every research note, the `derive`
children, those decisions as given, the split, the parent contract,
[../implement/references/contracts.md](../implement/references/contracts.md)
and the scratch path for its report. It writes one shared contract — at the
system level the API contract and the database schema, where the entities
live (for a human-first product, only what the first clickable slice needs,
served by the mock; the screens shape the rest as they land): every arrow typed, every piece of data with exactly one owner, every
conflict between the notes resolved with a reason — and, in the report, the
conflicts and what it could not resolve, listed for the user.

No separate critic: the seam check is part of `/vk-review` on the contract
PR. Run `/vk-consult critic` here only when the user asks.

## 5. Contract — gate

One pull request `contract/<node>-split`: the contract files where the
repository keeps contracts, `docs/modules.md` updated (one row per node:
parent, axis, path in the repository, status, contract path, owned data), and
a description that carries what the scratch directory will not keep:

- the lead's decisions from step 4, a numbered list, one line each with its
  reason;
- the integrator's report, verbatim: conflicts resolved with reasons, open
  questions;
- the requirement paths and sections the node answers to, which the seam
  check reads the contract against.

`/vk-review` reviews it as a boundary PR, seams included. The user approves
when the step 2 gate was theirs; otherwise `/vk-review`'s `accept` is enough.
Local mode: show it in chat and wait.

Fold the answers in by re-running the integrator from that description and
the current contract; seam findings from `/vk-review` too. Never patch the
contract by hand around it.

## 6. Hand off

One `backlog.md` line per child, in landing order (per `/vk-coding-style`).
Each child then goes to `/vk-implement` — which builds it if it is a leaf, or
comes back here if it is not.

Cost: one haiku errand, one sonnet agent per `research` child, one opus
integrator, plus one opus review of the contract PR. Say the number before
step 3 when it is more than six.
