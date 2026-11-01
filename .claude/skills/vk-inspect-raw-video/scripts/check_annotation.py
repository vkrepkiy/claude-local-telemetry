#!/usr/bin/env python3
"""Check a legacy events annotation's structure and frame references against a contact-sheet manifest.

For the current phases format use materialize_annotation.py instead. This catches impossible or inconsistent references; it cannot judge visual truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check(manifest: dict, annotation: dict) -> list[str]:
    issues = []
    frames = manifest["frames"]
    count = len(frames)
    if annotation.get("source_id") != manifest["source_id"]:
        issues.append("source_id does not match manifest")
    if not isinstance(annotation.get("overview"), str) or not annotation["overview"].strip():
        issues.append("overview is missing")
    frame_observations = annotation.get("frame_observations")
    if (not isinstance(frame_observations, list)
            or [x.get("frame") for x in frame_observations if isinstance(x, dict)] != list(range(1, count + 1))
            or len(frame_observations) != count):
        issues.append("frame_observations must contain every sampled frame exactly once in order")
    elif any(not isinstance(x.get("visible"), str) or not x["visible"].strip()
             for x in frame_observations):
        issues.append("every frame observation needs visible text")
    events = annotation.get("events")
    if not isinstance(events, list) or not events:
        return issues + ["events must be a nonempty list"]
    last_first = 0
    covered_frames = set()
    for position, event in enumerate(events, 1):
        if not isinstance(event, dict):
            issues.append(f"event {position}: must be an object")
            continue
        tag = event.get("id", f"event {position}")
        refs = event.get("evidence_frames")
        if not isinstance(refs, list) or not refs or any(not isinstance(n, int) or not 1 <= n <= count for n in refs):
            issues.append(f"{tag}: invalid evidence_frames")
            continue
        if refs != sorted(set(refs)):
            issues.append(f"{tag}: evidence_frames must be sorted and unique")
        covered_frames.update(refs)
        if refs[0] < last_first:
            issues.append(f"{tag}: events are not ordered by first observed frame")
        last_first = refs[0]
        if any(b - a > 1 for a, b in zip(refs, refs[1:])):
            issues.append(f"{tag}: evidence has an unobserved gap; split the event or inspect the gap")
        if not isinstance(event.get("observed"), str) or not event["observed"].strip():
            issues.append(f"{tag}: observed is missing")
        start = event.get("start") if isinstance(event.get("start"), dict) else {}
        end = event.get("end") if isinstance(event.get("end"), dict) else {}
        if start.get("status") == "bounded":
            if start.get("by_frame") != refs[0] or start.get("after_frame") != refs[0] - 1:
                issues.append(f"{tag}: bounded start must use the frame before first evidence and first evidence")
        elif start.get("status") == "already_in_progress":
            if refs[0] != 1 or start.get("by_frame") != 1:
                issues.append(f"{tag}: already_in_progress requires evidence and by_frame in first sampled frame")
        elif start.get("status") == "unclear":
            if start.get("by_frame") != refs[0] or start.get("after_frame") is not None:
                issues.append(f"{tag}: unclear start needs first evidence in by_frame and null after_frame")
        elif start.get("status") != "unclear":
            issues.append(f"{tag}: invalid start status")
        if end.get("status") == "bounded":
            if end.get("last_seen_frame") != refs[-1] or end.get("absent_by_frame") != refs[-1] + 1:
                issues.append(f"{tag}: bounded end must use last evidence and immediately following frame")
        elif end.get("status") == "continues_to_end":
            if refs[-1] != count or end.get("last_seen_frame") != count:
                issues.append(f"{tag}: continues_to_end requires evidence and last_seen_frame in last sampled frame")
        elif end.get("status") == "unclear":
            if end.get("last_seen_frame") != refs[-1] or end.get("absent_by_frame") is not None:
                issues.append(f"{tag}: unclear end needs final evidence in last_seen_frame and null absent_by_frame")
        elif end.get("status") != "unclear":
            issues.append(f"{tag}: invalid end status")
        certainty = event.get("certainty") if isinstance(event.get("certainty"), dict) else {}
        for key in ("observation", "interpretation"):
            if certainty.get(key) not in {"high", "medium", "low"}:
                issues.append(f"{tag}: invalid certainty.{key}")
        usability = event.get("usability") if isinstance(event.get("usability"), dict) else {}
        if usability.get("status") not in {
            "no_obvious_issue", "visible_issue", "needs_playback"
        }:
            issues.append(f"{tag}: invalid usability.status")
        project_relevance = event.get("project_relevance") if isinstance(event.get("project_relevance"), dict) else {}
        if project_relevance.get("status") not in {
            "main_action", "context", "unlikely", "unclear", "unassessed"
        }:
            issues.append(f"{tag}: invalid project_relevance.status")
    uncovered = sorted(set(range(1, count + 1)) - covered_frames)
    if uncovered:
        issues.append(f"sampled frames without any event/state: {uncovered}")
    requests = annotation.get("review_requests")
    if not isinstance(requests, list):
        issues.append("review_requests must be a list")
    else:
        for i, request in enumerate(requests, 1):
            if not isinstance(request, dict):
                issues.append(f"review request {i}: must be an object")
                continue
            pair = request.get("between_frames")
            time_range = request.get("time_range_seconds")
            pair_ok = (isinstance(pair, list) and len(pair) == 2
                       and all(isinstance(n, int) and 1 <= n <= count for n in pair)
                       and pair[0] < pair[1])
            range_ok = (isinstance(time_range, list) and len(time_range) == 2
                        and all(isinstance(n, (int, float)) for n in time_range)
                        and 0 <= time_range[0] < time_range[1] <= manifest["duration_seconds"])
            if not (pair_ok or range_ok):
                issues.append(f"review request {i}: give valid between_frames or time_range_seconds")
            if not isinstance(request.get("question"), str) or not request["question"].strip():
                issues.append(f"review request {i}: question is missing")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("annotation", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    annotation = json.loads(args.annotation.read_text())
    if isinstance(annotation, dict) and "phases" in annotation and "events" not in annotation:
        print(f"{args.annotation} uses the current phases format; this checker is for legacy events "
              "annotations only. Validate it with materialize_annotation.py MANIFEST DRAFT OUTPUT.",
              file=sys.stderr)
        return 1
    issues = check(manifest, annotation)
    if issues:
        print("\n".join(f"- {issue}" for issue in issues))
        return 1
    print(f"OK: {len(annotation['events'])} events, {len(manifest['frames'])} source frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
