---
name: vk-compass
description: Check whether proposed work serves the repository's goal - GOAL.md, the owner's short file of why the repository exists and its key scenarios, read first and winning over backlog.md, the design docs, the decision record and docs/rejected.md - and say whether it belongs now, next, later, is a detour or goes against a decision, with the smallest route inside the goal and the backlog line to paste. With no GOAL.md it judges nothing - it drafts one and asks the owner. Recommends, never blocks. Use on its own when the user proposes work that is not already a line of `## Now` or `## Next` - "давай сделаем", "хочу фичу", "нужно добавить", "let's add", "I want it to…" - and when the user says "compass", "does this serve the goal", "это нам нужно?", "зачем мы это делаем", "write the goal", "напиши цель". Not for a bug (that is /vk-regression), continuing a backlog line, a question or a discussion with no work asked, or a wording or typo change.
argument-hint: '[the proposal; `goal` to write or revise GOAL.md; or nothing to take it from the conversation]'
---

One agent reads what the repository says it is for and tells whether the
proposed work serves it. Late in a project nobody discusses any more; this is
where drift is caught — the owner can drift, the agent doing the work can
drift, so a separate agent watches. It recommends; the user decides.

Input for this run: $ARGUMENTS

## 1. The goal

`GOAL.md` at the repository root is the owner's: why this repository
exists and what it holds, the key scenarios, what is not done — the shape is
in [references/goal.md](references/goal.md). It is the first source and it
wins. A part of the repository with its own `GOAL.md` (a role, an app) is
judged against that file first, then the root.

- No `GOAL.md`, or `$ARGUMENTS` is `goal`: judge nothing, go to step 5.
- Over 40 lines, or a section of that shape missing: say so in one line at
  the top of the report, every run, until the owner fixes it. Do not fix it.

## 2. The proposal

From `$ARGUMENTS`, or else the conversation: what the user asked for and the
problem they want gone, in at most five lines, in their own words. Quote it,
do not improve it — a tidied proposal already argues for itself.

Do not run when the proposal is already a line of `## Now` or `## Next`, or
when the user reaffirmed it after a verdict: the work proceeds, and this
proposal is not checked again.

## 3. Spawn one agent

One **`vk-compass`** agent. Raise it to `model: opus` for one case only: the
proposal is big enough that `/vk-implement` would send it to `/vk-split` —
several modules, its own design decisions, more than a day of work.

> Proposal, in the user's words:
>
> \<the proposal\>
>
> Repository: \<absolute path of its root\>. Read its `GOAL.md` first. Then
> the rest of its written intent: `backlog.md` (`## Now` is here and now,
> `## Next` the next iteration in order, `## Later` recorded, not planned);
> `README.md` and the design docs; the decision record (`docs/decisions.md`,
> ADRs, a `## Decisions` section in a design doc); and `docs/rejected.md`.
> Where any of them disagrees with `GOAL.md`, the verdict follows `GOAL.md`
> and names the disagreement.
>
> The verdict is exactly one of:
>
> - `now` — serves a key scenario of `GOAL.md` through the `## Now` handoff
>   or the first line of `## Next`;
> - `next` — serves a key scenario through a later line of `## Next`;
> - `later` — serves a key scenario of `GOAL.md`, but nothing planned;
>   belongs in `## Later`;
> - `detour` — serves no key scenario, including a real problem solved by a
>   route the goal does not ask for, and a backlog line that serves none;
> - `against` — contradicts a line of `GOAL.md`'s non-goals, a recorded
>   decision or a rejected option; cite it.
>
> Reply in the language of the proposal, at most 15 lines:
>
> **Verdict:** \<word\> — \<one line why\>
>
> **Serves:** \<the key scenario of `GOAL.md`, quoted, and the backlog line
> it falls under, quoted\> or "no key scenario"
>
> **Disagrees:** \<the source that contradicts `GOAL.md`, or the backlog
> line that serves no key scenario, quoted with its
> path\> — only when one does
>
> **Displaces:** \<what in `## Now` or the first `## Next` line waits while this is done\>
>
> **Simplest route:** \<the smallest change that gets the same outcome inside
> the goal\> — only when the proposal is bigger than that
>
> **Recommend:** do it now · add to `## Next` as pN · add to `## Later` · drop
>
> Unless you recommend "do it now", write out the line to paste: the backlog
> line in the shape of the lines already in `backlog.md`, an outcome in the
> user's words, never a file or a step; for drop, the `docs/rejected.md` line.
>
> If the proposal is a bug, already a backlog line or no work at all, reply
> only `**Verdict:** not applicable — <why>`.

## 4. Report

The agent's reply as it wrote it, under the line from step 1 if there is
one. It recommends, it never blocks — see `/vk-coding-style`, "Recommend,
don't dictate". When the user reaffirms, the work proceeds. When they
reaffirm against a `detour` and their reason shows the goal itself changed,
offer the `GOAL.md` edit through step 5 — never make it silently. A line the
user accepts is written to `backlog.md` or `docs/rejected.md` per
`/vk-coding-style`, Backlog; nothing else is written.

## 5. Write the goal

One **`vk-compass`** agent drafts `GOAL.md` — or the revision the owner
asked for — in the shape of [references/goal.md](references/goal.md), from
`README.md`, the design docs, `backlog.md` and what the owner said in this
conversation (quote it into the spawn), in the owner's words where they
exist. It replies with the draft and at most five
questions, one per guess: a section it could not fill, a scenario it
inferred, a non-goal it assumed.

Show both. On the owner's ok — the reply may be a corrected draft — write
`GOAL.md` and commit it alone as `docs(goal): why this repository exists`
(a revision: `docs(goal): <what changed>`). A proposal that was waiting
for the file then goes on to step 2.
