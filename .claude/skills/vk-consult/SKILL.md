---
name: vk-consult
description: Get critique from specialist roles - critic, pm, architect, marketer, psychologist (roles/*.md) - each running as its own parallel subagent. Use when the user asks for a second opinion, a critique or a specialist's take, or says "consult", "poke holes in this", "what would a PM say", "запусти критика", "позови продакта", "что скажет архитектор".
argument-hint: '[role...] or "all"'
---

Each named role looks at what is being discussed through its own lens,
investigates the repository, and returns one short note. Roles run in
parallel and never see each other's reasoning.

Input for this run: $ARGUMENTS

## 1. The brief

Write down, in at most fifteen lines, what is being discussed: the idea, the
decision on the table, and what the user is unsure about — from the
conversation, in the user's own words where possible. Add the absolute paths
of anything relevant: code, contracts, a PR, a design link. This brief is all
a role gets besides the repository, so make it stand alone.

## 2. The roles

Run exactly the roles the user named. `all` means every file in
`roles/` — deliberate and expensive, each role is a separate opus call. With
no role named, pick the smallest set the topic calls for, usually `critic`
alone or `critic` + `pm`, and say which in one line.

The roles live in `roles/` at the plugin root, two levels above this skill's
base directory.

## 3. Spawn them in parallel

All calls in one message, each as the **`vk-role`** agent, with this prompt:

> You are consulting in the role of **\<role\>**. Read `<roles dir>/<role>.md`
> for your lens, then this brief:
>
> \<the brief\>
>
> Investigate the repository for anything you intend to assert; a point that
> could be made without opening it is worthless. Reply in at most 25 lines:
>
> **Verdict:** \<the one thing you most need to say\>
>
> **Points** — at most 5, each grounded in something you read
>
> **Risks** — at most 3, each with the signal that would show it happening
>
> **Would change** — at most 3 concrete changes
>
> If your lens does not apply, reply only `**Verdict:** not applicable — <why>`.

## 4. Report

For each role: its verdict line and its points, as it wrote them — do not
blend them into a consensus. Then name every place two roles contradict each
other; that is the most useful part of the run.

Nothing is written to disk unless the user asks. When a decision comes out of
it, it belongs where the work is recorded: the contract PR, `backlog.md`, or
the repository's docs.
