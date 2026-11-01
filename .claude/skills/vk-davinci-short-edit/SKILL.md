---
name: vk-davinci-short-edit
description: Assemble an approved short-form edit plan into an editable DaVinci Resolve timeline from the real footage, render a candidate for producer and user review, then finish and export - every claim matched to the footage, every deliverable checked on the rendered file. Use when an edit_plan.json is approved and the user says "собери монтаж", "смонтируй в DaVinci", "отрендери превью", "assemble the edit", "render it in Resolve". Typed only - it writes into Resolve's project database and renders outside the repository. Not for planning (short-edit-planning) or inspecting footage (inspect-raw-video).
disable-model-invocation: true
argument-hint: '[the approved edit_plan.json and the deliverables wanted]'
---

Turn the approved plan and the original footage into a Resolve timeline the
user can keep editing, and the exports they asked for. The plan is the design;
the footage is the evidence. Never change the story silently, invent a visible
action, or put a generated image where a real shot has to prove something.

Input for this run: $ARGUMENTS

## 0. Resolve is reachable

Resolve running with a project open, and Preferences → System → General →
External scripting using: Local. `python3 scripts/render_preview_resolve.py
--dry-run OUTPUT` connects and reports. If it cannot, stop and tell the user
exactly what to enable — external scripting may need DaVinci Resolve Studio.
No ffmpeg-only edit instead without their word.

## 1. Plan and footage

- The plan has `approval_status: approved` and an `approved_variant`;
  otherwise stop and send the user back to `/vk-short-edit-planning`.
- Probe every source: fps and whether it varies, rotation, audio, missing
  files. Originals are never modified.
- Every range marked approximate is checked on the footage before it becomes
  frames — dense contact sheets of that stretch (`/vk-inspect-raw-video`,
  short `--interval`) and the decisive action as a whole. Record the actual
  in/out and every deviation from the plan.
- Frames are `round(seconds × brief.fps)`, source out exclusive — the
  half-open interval `AppendToTimeline` uses. Beat ids from the plan carry
  through the manifest and the report.

## 2. Candidate cut

You are the editor and own the timeline. Write the assembly script yourself
from a frame manifest — beat, source, range, track, transform — following
[resolve-api.md](references/resolve-api.md), and check every API result.
Original or scratch sound, title placeholders at their timing. Reframe a shot
only after checking its beginning, middle and end at the output aspect.

Render a preview per [rendering.md](references/rendering.md) — a low-cost
model can run it (`vk-errand` on Claude, Luna on OpenAI) — and verify it
(step 4). Then the producer: one subagent on a strong model (`vk-role` on
Claude) wearing `roles/producer.md` (the `roles/` directory two levels above
this skill's), given the plan, the edit report and contact sheets of the
rendered preview at a short interval. A model reviews frames, not playback,
and cannot hear: real-time pacing and sound are the user's to judge. Fix
factual and technical blockers, then give the user the preview and the
producer's advice. This is a candidate cut; only the user's approval locks
the picture.

## 3. Finish

After the picture is approved: titles, number graphics and emphasis shapes
as separate, editable assets. Music and effects only from files the user
supplied or whose licence they confirmed — nothing generated or downloaded
without that. Sound and graphics may be separate subagents when their work
outweighs the hand-off ([workflow.md](references/workflow.md)); you alone
integrate them into the project. Export the project and the requested files.

## 4. Verify the rendered files

`python3 scripts/qa_render.py PREFIX --require preview,report,…` checks the
frame count against the report, fps, audio, clipping and one-frame black gaps.
It cannot see crop, legibility, safe area or whether a claim is true — look at
the frames for those. The report is JSON with at least
`{"timeline": {"frames": N, "fps": F}}`, plus every source used with its
in/out, alternates, deviations from the plan, generated assets and
editability limits. A deliverable is done when its file exists and passed its
check; a script finishing proves nothing.

## What must hold

- Every on-screen claim matches what is visible; an unproven one becomes a
  question or goes.
- Originals untouched; generated and derived assets kept apart and named in
  the report, with any loss of editability — a flattened stem, a rendered
  title.
- Integer frames everywhere; cut boundaries checked on the rendered file.
- Phone safe area, crop, legibility and the first seconds judged on the
  export, not on the source.
