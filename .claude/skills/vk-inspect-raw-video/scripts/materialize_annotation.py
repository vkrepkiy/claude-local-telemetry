#!/usr/bin/env python3
"""Validate simple phase ranges and derive timing from FFmpeg's actual frame PTS."""

import argparse
import json
import sys
from pathlib import Path


def is_one_of(value, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def materialize(manifest: dict, draft: dict) -> tuple[dict, list[str]]:
    """Return the materialized annotation and the problems found; write it only when there are none."""
    frames = manifest["frames"]
    count = len(frames)
    issues = []
    if draft.get("source_id") != manifest["source_id"]:
        issues.append("source_id mismatch")
    observations = draft.get("frame_observations", [])
    if not isinstance(observations, list) or not all(isinstance(x, dict) for x in observations) or [x.get("frame") for x in observations] != list(range(1, count + 1)):
        issues.append("frame_observations must cover every frame once in order")
    elif any(not isinstance(x.get("visible"), str) or not x["visible"].strip() for x in observations):
        issues.append("frame_observations contain empty descriptions")
    if not isinstance(draft.get("overview"), str) or not draft["overview"].strip():
        issues.append("overview missing or empty")
    phases = draft.get("phases", [])
    if not isinstance(phases, list) or not phases:
        issues.append("phases missing")
    covered = set()
    last_first = 0
    seen_ids = set()
    output = json.loads(json.dumps(draft))
    for phase in output.get("phases", []) if isinstance(output.get("phases"), list) else []:
        if not isinstance(phase, dict):
            issues.append("phase must be an object")
            continue
        tag = phase.get("id")
        if not isinstance(tag, str) or not tag.strip():
            issues.append(f"phase {tag!r}: id must be a non-empty string")
            tag = repr(tag)
        elif tag in seen_ids:
            issues.append(f"{tag}: duplicate phase id")
        seen_ids.add(tag)
        first, last = phase.get("first_frame"), phase.get("last_frame")
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= count:
            issues.append(f"{tag}: invalid frame range")
            continue
        if first < last_first:
            issues.append(f"{tag}: phases out of order")
        last_first = first
        covered.update(range(first, last + 1))
        onset, offset = phase.get("onset"), phase.get("offset")
        if not is_one_of(onset, {"open", "bounded", "unclear"}) or (onset == "open") != (first == 1):
            issues.append(f"{tag}: invalid onset for first frame")
        if not is_one_of(offset, {"open", "bounded", "unclear"}) or (offset == "open") != (last == count):
            issues.append(f"{tag}: invalid offset for last frame")
        if not isinstance(phase.get("observed"), str) or not phase["observed"].strip():
            issues.append(f"{tag}: empty observed")
        certainty = phase.get("certainty")
        levels = {"high", "medium", "low"}
        if not isinstance(certainty, dict) or not is_one_of(certainty.get("observation"), levels):
            issues.append(f"{tag}: invalid certainty")
        elif not is_one_of(certainty.get("interpretation"), levels) and not (
                phase.get("interpretation") is None and certainty.get("interpretation") is None):
            # A phase with no interpretation may leave its certainty null too.
            issues.append(f"{tag}: invalid certainty")
        usability = phase.get("usability")
        if not isinstance(usability, dict) or not is_one_of(usability.get("status"), {"no_obvious_issue", "visible_issue", "needs_playback"}):
            issues.append(f"{tag}: invalid usability")
        relevance = phase.get("project_relevance")
        if not isinstance(relevance, dict) or not is_one_of(relevance.get("status"), {"main_action", "context", "unlikely", "unclear", "unassessed"}):
            issues.append(f"{tag}: invalid project_relevance")
        if not isinstance(phase.get("unknowns"), list):
            issues.append(f"{tag}: unknowns must be a list")
        phase["start_window_seconds"] = (
            None if first == 1 or onset != "bounded" else
            [frames[first - 2]["actual_seconds"], frames[first - 1]["actual_seconds"]]
        )
        phase["end_window_seconds"] = (
            None if last == count or offset != "bounded" else
            [frames[last - 1]["actual_seconds"], frames[last]["actual_seconds"]]
        )
        phase["first_visible_seconds"] = frames[first - 1]["actual_seconds"]
        phase["last_visible_seconds"] = frames[last - 1]["actual_seconds"]
    missing = sorted(set(range(1, count + 1)) - covered)
    if missing:
        issues.append(f"uncovered frames: {missing}")
    requests = output.get("review_requests", [])
    if not isinstance(requests, list):
        issues.append("review_requests must be a list")
    else:
        for n, request in enumerate(requests, 1):
            if not isinstance(request, dict) or type(request.get("first_frame")) is not int or type(request.get("last_frame")) is not int or not 1 <= request["first_frame"] <= request["last_frame"] <= count:
                issues.append(f"review_request {n}: invalid frame range")
            if not isinstance(request, dict) or not isinstance(request.get("question"), str) or not request["question"].strip():
                issues.append(f"review_request {n}: question missing or empty")
    output["schema_version"] = 2
    output["review_status"] = "draft"
    return output, issues


def check_review(record: dict) -> list[str]:
    """A review record names who checked the draft against the pages and what remains open."""
    issues = []
    if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        issues.append("review: reviewer must be a non-empty string")
    for key in ("corrections", "unknowns"):
        value = record.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            issues.append(f"review: {key} must be a list of strings")
    return issues


def read_object(path: Path, label: str, issues: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        issues.append(f"{label} {path}: cannot read JSON: {error}")
        return {}
    if not isinstance(value, dict):
        issues.append(f"{label} {path}: must be a JSON object")
        return {}
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="manifest.json written by contact_sheets.py")
    parser.add_argument("draft", type=Path, help="annotation draft JSON from the model")
    parser.add_argument("output", type=Path, help="where to write the materialized annotation")
    parser.add_argument("--review", type=Path, metavar="RECORD.json",
                        help='review record {"reviewer": str, "corrections": [str], "unknowns": [str]}; '
                             "marks the output review_status verified")
    args = parser.parse_args()
    issues: list[str] = []
    manifest = read_object(args.manifest, "manifest", issues)
    draft = read_object(args.draft, "draft", issues)
    review = None
    if args.review is not None:
        review = read_object(args.review, "review", issues)
        issues += check_review(review)
    if not issues and not isinstance(manifest.get("frames"), list):
        issues.append(f"manifest {args.manifest}: no frames list")
    if not issues:
        result, issues = materialize(manifest, draft)
    if not issues and review is not None:
        result["review_status"] = "verified"
        result["review"] = review
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(result['phases'])} phases, {len(result['frame_observations'])} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
