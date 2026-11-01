---
name: vk-short-edit-planning
description: Plan a short-form edit from inspected footage - pick evidence-backed fragments, alternates, a hook, titles and sound for each variant, mark what is unproven or missing, and stop at the user's approval with an edit_plan.json the assembly reads. Use when the footage has been inventoried and the user wants a plan, a shot list or variants for a short, or says "спланируй монтаж", "план шортса", "выбери дубли", "из чего собрать ролик", "plan the edit". Not for inspecting footage (inspect-raw-video) or assembling a timeline (davinci-short-edit).
argument-hint: '[the brief - story, platform, length - and the inventory index.json]'
---

Between the inventory and the timeline: a plan the user approves before
anything is assembled. The plan never claims more than the footage shows.

Input for this run: $ARGUMENTS

## Inputs

- `index.json` from `/vk-inspect-raw-video` (`scripts/build_inventory.py`):
  every source with its path, duration, fps, manifest, annotation and review
  status.
- A brief: the story, platform, aspect ratio, target length, timeline fps,
  the beats it needs. Ask for what is missing; do not invent the story.

Do not launch a new analysis of the whole collection. A `draft` annotation is
evidence with uncertainty, not verification. Sampled frames give windows, not
cut points.

## Method

1. Split the material by the beats the brief needs — for example hook, setup,
   action, reveal, end card. A file may give several fragments.
2. For each beat pick the strongest continuous fragment and list alternates
   from other takes. Keep for each its source, range, the annotation phases it
   rests on, and any visible usability problem.
3. Each variant opens with a hook ending by `brief.hook_seconds` (3 s unless
   the brief says otherwise). No usable hook in the footage: a gap and a
   proposed generated treatment — text, a freeze, a sound hit, a graphic —
   never pretending it was filmed.
4. Every story claim is `confirmed` (visible in a verified annotation, or
   confirmed by the user), `supported_but_unproven` (seen only in a draft, or
   inferred between samples) or `missing_or_unverified`. An unproven claim may
   be framed as a question, never stated as fact. Nothing is inferred from
   proximity, gaze or a single frame.
5. Times stay in seconds from the manifests, marked approximate wherever the
   annotation gives a window rather than a boundary. Frames are fixed at
   assembly, from `brief.fps`, after the footage is checked.

## Output

`edit_plan.json` per [edit-plan.md](references/edit-plan.md), then
`python3 scripts/validate_edit_plan.py edit_plan.json INDEX` until it prints
`VALID`. The validator checks structure and references; what the footage
shows is still your claim to defend.

## Approval

Show the user the variants, the risks and the open questions, and stop. On
their explicit choice set `approval_status: approved` and `approved_variant`,
validate again, and tell them the next step is `/vk-davinci-short-edit` — it
does not start on its own.
