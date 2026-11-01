# Annotation contract, legacy `events` format

Only for reading and checking annotation files written in the old `events` format; write new ones with [annotation-contract.md](annotation-contract.md). Check these with `scripts/check_annotation.py`.

## First-pass instruction to the vision model

Fill `SOURCE_ID`, `DURATION`, and the page list from `manifest.json`. Attach the manifest and all pages in page order. If the user has stated the intended video's subject, also give a one-sentence `PROJECT_BRIEF`; use it only for the separate `project_relevance` field.

> These images are chronological samples from **one continuous raw video file**, not screenshots of a completed edit. Every tile has its own frame number and actual video timestamp printed immediately **below that tile**. Every page belongs to `SOURCE_ID`. Read all pages before answering. The source duration is `DURATION` seconds. Between sampled frames, the action is unobserved. First write one short literal observation for **each sampled frame**, including salient subject, human hand, object, and visible contact when present. Do not lose a simultaneous animal action because a hand dominates the frame. Then give a one-sentence overview of the whole file. List distinct visible action or state phases in temporal order, including waiting, repeated attempts, major camera reframing, and human handling where relevant. A phase can overlap another phase; a continuing background state can overlap a brief action. **Every sampled frame must belong to at least one event or state.** Split when the meaningful action, subject, or outcome changes; never combine disjoint appearances of a subject into one continuous event. Each event describes one coherent phase, and `evidence_frames` lists only frames where that phase is actually visible. A stable background object may be one state, but do not fold its brief movement into that state if the movement has its own event. Do not duplicate the same brief action in both the background state and the action event. Boundary fields separately identify adjacent frames without the phase. A persistent state ends only when it actually ceases in a sampled frame; a new overlapping action does not terminate it. Use literal visual descriptions; distinguish visible facts from interpretations. Describe spatial relations as separated, adjacent, or visibly touching; movement toward an object does not prove that it reaches that object. Do not assert physical contact unless it is visible. Never infer choice, intention, causation, speech, or what happened between samples without evidence. For each phase cite frame numbers and the observed onset/end window. If already in progress in the first frame or still in progress in the last, leave that boundary open. Note obvious framing, obstruction, or lighting problems only for the frames belonging to that event; do not judge fine focus, shake, or sound from a contact sheet. If a `PROJECT_BRIEF` is provided, assess possible use in that project separately from visual observations; this is a tentative tag, never a reason to erase a source. Tag props or setup alone as `context`; use `main_action` only when the specified action itself is visible. Put an uncertainty into `review_requests` only when the *observed frames* show a specific unresolved transition, contact, occlusion, or changed object state. Missing plot beats from `PROJECT_BRIEF` do not justify speculative review requests. Before responding, check every event against its cited frames, check that no event contradicts its own start/end fields, and check coverage of all sampled frames. Return only JSON following the contract below. Do not refer to frames from any other file.

## JSON fields

```json
{
  "source_id": "exact manifest source_id",
  "frame_observations": [
    {"frame": 1, "visible": "literal one-line observation"}
  ],
  "overview": "one sentence about the whole take",
  "events": [
    {
      "id": "E01",
      "observed": "literal change or state visible in sampled frames",
      "interpretation": "action implied by the sequence, or null",
      "evidence_frames": [1, 2, 3],
      "start": {"status": "bounded", "after_frame": 1, "by_frame": 2},
      "end": {"status": "bounded", "last_seen_frame": 3, "absent_by_frame": 4},
      "certainty": {
        "observation": "high",
        "interpretation": "medium",
        "reason": "short reason for uncertainty, if any"
      },
      "usability": {
        "status": "no_obvious_issue",
        "visible_reason": null
      },
      "project_relevance": {
        "status": "unassessed",
        "reason": null
      },
      "unknowns": []
    }
  ],
  "review_requests": [
    {"between_frames": [3, 4], "time_range_seconds": null, "question": "Did the kitten actually touch the food?", "reason": "outcome not visible in overview samples"}
  ]
}
```

Allowed `start.status`: `bounded`, `already_in_progress`, `unclear`. Allowed `end.status`: `bounded`, `continues_to_end`, `unclear`. For `bounded` start, `after_frame` is the last observed frame without that phase and `by_frame` is the first observed frame with it. For `bounded` end, `last_seen_frame` is the last observed frame with the phase and `absent_by_frame` is the first observed frame without it. Use `null` for inapplicable frame fields. If both onset and offset fall between the same two sampled frames and the action itself is unseen, do not invent an event; record a `review_requests` question about the apparent change.

Use `unclear` when an adjacent frame is cropped, blurred, occluded, or aimed elsewhere, so it cannot establish that a phase was absent. Keep the first or last visible evidence frame in `by_frame` or `last_seen_frame`, and set the unsupported neighbor field to `null`. This is distinct from `bounded`, which requires visible evidence of absence on the neighbor frame.

Allowed certainty values: `high`, `medium`, `low`. They evaluate the visual observation and the action interpretation separately. The boundary's uncertainty is expressed by the pair of actual frame times in the manifest, not by a confidence number. Allowed usability values: `no_obvious_issue`, `visible_issue`, `needs_playback`. Contact sheets can support gross framing, occlusion, and lighting observations; `needs_playback` covers motion, sound, and other qualities requiring video playback. Avoid rating resolution or 4K sharpness.

`frame_observations` has exactly one entry for every sampled frame in numeric order. Keep each entry short, literal, and spatially precise. It is an audit trail for the event summary, not another full caption. If a project brief is supplied, allowed `project_relevance.status` values are `main_action`, `context`, `unlikely`, `unclear`; otherwise use `unassessed`. `main_action` requires **one** of the brief's named actions itself to be visible; the entire plot need not occur in one file. If the brief says someone draws, visible pencil marks being made can be `main_action` even if their identity and the final picture are unknown; note those unknowns separately. If the brief says an animal chooses among objects, merely facing or approaching them is `context`; selection requires direct behavioral evidence. `project_relevance` is provisional. It never deletes a source or overrides `observed` and `certainty`.

An event list should cover the meaningful visible progression of the source. Long stretches with no meaningful change can be one state. Keep alternative actions inside a source as separate events; do not pick a winner for the eventual edit.

`evidence_frames` must be sorted and refer only to frames where `observed` is supported. Do not use an absent frame as evidence for a visible action; put it in the boundary object. A `bounded` start and end use consecutive sampled frame IDs. If a phase disappears and reappears after one or more samples, make separate events unless the images actually establish continuity. `review_requests.between_frames` may span more than one sampling interval when the camera points away or an important action stays occluded.

For a review range after the last sampled frame or before the first one, use `between_frames: null` and `time_range_seconds: [start, end]`, both within the source duration. Never ask about "later" if the requested range stops at the last overview sample before the video ends.

For `already_in_progress`, set `by_frame` to `1`. For `continues_to_end`, set `last_seen_frame` to the final frame number. A persistent bed/background state may overlap a shorter cat action; this keeps all sampled frames accounted for without artificial cuts in the underlying continuous take.

If an action interpretation is `medium` or `low` certainty, explain the specific missing evidence. Put it in `review_requests` when another sample from a bounded interval could resolve an important point; otherwise put it in that event's `unknowns`. Do not leave both lists empty while the reason states that an important action remains uncertain. A generic fact that motion between sampled frames is unseen does not alone require resampling.

## Detail pass

A detail range has its own `sample_set_id` in the manifest. Its frame numbers restart at 1, so always cite both `sample_set_id` and detail frame number; never merge them with overview frame numbers. Give the model the original annotation, the specific unresolved question, the detail manifest, and its sheets. Ask only for a short answer with directly visible evidence and a proposed correction to the affected overview event. If the detail still cannot resolve the question, retain it as unknown. Do not regenerate a full-file summary from the range alone.

## Independent visual review

Use a different, stronger vision model or a human for candidate files. Give the same manifest and **all** overview sheets, the draft JSON, and the project brief. Use this instruction:

> Audit this annotation against the images, not against the previous model's confidence. Read every tile yourself. Report only concrete factual errors, missing simultaneous actions, incorrect spatial relations or contact, event duplication, false onset/end boundaries, missed visible objects, and unwarranted relevance or usability tags. Cite frame IDs and the exact JSON field. In particular, check the primary subject's face or action is not cropped or hidden before accepting `no_obvious_issue`. Treat a single still as a position, not proof of a movement path. Do not invent a missing plot beat. Return a concise correction list and unresolved questions. If no issue remains, say so explicitly.

Apply corrections to a new annotation file. Re-run `scripts/check_annotation.py`. Keep the review record alongside that revision; a passing checker is not a visual audit. If the reviewer raises a specific question that overview frames cannot settle, sample only the indicated interval at a finer cadence. A second reviewer pass should confirm that the corrections were applied; after that, leave any unresolved claim explicitly uncertain rather than repeating broad re-prompts indefinitely.
