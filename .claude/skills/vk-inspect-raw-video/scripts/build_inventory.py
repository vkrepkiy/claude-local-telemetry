#!/usr/bin/env python3
"""Build the footage inventory index.json that short-edit-planning reads.

Scans SHEETS_ROOT/*/overview/manifest.json, the layout contact_sheets.py writes.
A source's materialized annotation, when there is one, is SHEETS_ROOT/<source dir>/annotation.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REVIEW_STATUSES = {"draft", "verified"}


def read_object(path: Path, issues: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        issues.append(f"{path}: cannot read JSON: {error}")
        return None
    if not isinstance(value, dict):
        issues.append(f"{path}: must be a JSON object")
        return None
    return value


def relative_to_index(path: Path, index_directory: Path) -> str:
    return Path(os.path.relpath(path.resolve(), index_directory.resolve())).as_posix()


def describe_source(manifest_path: Path, index_directory: Path, issues: list[str]) -> dict | None:
    manifest = read_object(manifest_path, issues)
    if manifest is None:
        return None
    for key in ("source_id", "source_path", "duration_seconds"):
        if key not in manifest:
            issues.append(f"{manifest_path}: {key} missing")
            return None
    entry = {
        "source_id": manifest["source_id"],
        "path": manifest["source_path"],
        "duration_seconds": manifest["duration_seconds"],
        "fps": manifest.get("fps"),
        "manifest": relative_to_index(manifest_path, index_directory),
        "annotation": None,
        "review_status": "not_annotated",
        "main_action_phases": [],
    }
    annotation_path = manifest_path.parents[1] / "annotation.json"
    if not annotation_path.exists():
        return entry
    annotation = read_object(annotation_path, issues)
    if annotation is None:
        return None
    if annotation.get("source_id") != manifest["source_id"]:
        issues.append(f"{annotation_path}: source_id {annotation.get('source_id')!r} "
                      f"does not match its manifest's {manifest['source_id']!r}")
        return None
    status = annotation.get("review_status")
    if status not in REVIEW_STATUSES:
        issues.append(f"{annotation_path}: review_status must be draft or verified; "
                      "materialize the draft with materialize_annotation.py")
        return None
    phases = annotation.get("phases")
    if not isinstance(phases, list) or not all(isinstance(phase, dict) for phase in phases):
        issues.append(f"{annotation_path}: phases must be a list of objects")
        return None
    entry["annotation"] = relative_to_index(annotation_path, index_directory)
    entry["review_status"] = status
    entry["main_action_phases"] = [
        phase.get("id") for phase in phases
        if isinstance(phase.get("project_relevance"), dict)
        and phase["project_relevance"].get("status") == "main_action"
    ]
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheets_root", type=Path, help="output directory of contact_sheets.py")
    parser.add_argument("--output", type=Path, help="where to write the index (default SHEETS_ROOT/index.json)")
    args = parser.parse_args()
    if not args.sheets_root.is_dir():
        parser.error(f"{args.sheets_root} is not a directory")
    output = args.output or args.sheets_root / "index.json"
    issues: list[str] = []
    manifests = sorted(args.sheets_root.glob("*/overview/manifest.json"))
    if not manifests:
        issues.append(f"{args.sheets_root}: no */overview/manifest.json found; run contact_sheets.py first")
    sources = [describe_source(path, output.parent, issues) for path in manifests]
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    sources.sort(key=lambda source: source["path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema_version": 1, "sources": sources},
                                 indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    annotated = sum(source["review_status"] != "not_annotated" for source in sources)
    verified = sum(source["review_status"] == "verified" for source in sources)
    print(f"OK: {len(sources)} sources, {annotated} annotated, {verified} verified -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
