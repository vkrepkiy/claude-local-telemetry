#!/usr/bin/env python3
"""Structural validator for approval-gated edit_plan.json files (schema version 2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 2
DEFAULT_HOOK_SECONDS = 3.0
DURATION_TOLERANCE_SECONDS = 0.05
CONFIDENCE_LEVELS = ("confirmed", "supported_but_unproven", "missing_or_unverified")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check an edit_plan.json against the raw-footage inventory it cites.",
    )
    parser.add_argument("plan", metavar="PLAN", type=Path, help="the edit_plan.json to check")
    parser.add_argument("inventory", metavar="INVENTORY", type=Path, help="the inventory index.json")
    return parser.parse_args()


def load_json(path: Path, problems: list[str]):
    """Return the parsed file, or None after recording why it could not be read."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        problems.append(f"{path}: cannot read: {error.strerror or error}")
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        problems.append(f"{path}: not valid JSON: {error}")
    return None


def load_object(path: Path, name: str, problems: list[str]) -> dict | None:
    """Return the parsed file when it is a JSON object; record a problem otherwise."""
    known_problems = len(problems)
    value = load_json(path, problems)
    if len(problems) == known_problems and not isinstance(value, dict):
        problems.append(f"{name} must be a JSON object, got {type(value).__name__}")
    return value if isinstance(value, dict) else None


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_positive_number(value) -> bool:
    return is_number(value) and value > 0


def list_objects(container: dict, key: str, label: str, problems: list[str]) -> list[dict]:
    """Return container[key] when it is a list, keeping only its objects and reporting the rest."""
    value = container.get(key)
    if not isinstance(value, list):
        problems.append(f"{label}: {key} must be a list")
        return []
    objects = []
    for position, item in enumerate(value):
        if isinstance(item, dict):
            objects.append(item)
        else:
            problems.append(f"{label}: {key}[{position}] must be an object")
    return objects


def read_numbers(record: dict, keys: tuple[str, ...], label: str, problems: list[str]) -> list[float] | None:
    """Return the values under keys when all are numbers; report each one that is not."""
    values = [record.get(key) for key in keys]
    for key, value in zip(keys, values):
        if not is_number(value):
            problems.append(f"{label}: {key} must be a number, got {value!r}")
    return values if all(is_number(value) for value in values) else None


def collect_ids(records: list[dict]) -> set[str]:
    return {record["id"] for record in records if isinstance(record.get("id"), str)}


def is_known_id(value, known_ids: set[str]) -> bool:
    return isinstance(value, str) and value in known_ids


class Inventory:
    """The inventory's sources, with each source's annotation ids read on first use."""

    def __init__(self, index: dict, directory: Path, problems: list[str]):
        self.directory = directory
        self.problems = problems
        self.by_id = self.index_sources(index)
        self.annotation_ids: dict[str, set[str] | None] = {}

    def index_sources(self, index: dict) -> dict[str, dict]:
        sources = index.get("sources")
        if not isinstance(sources, list):
            self.problems.append("inventory: sources must be a list")
            return {}
        by_id = {}
        for position, source in enumerate(sources):
            if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
                self.problems.append(f"inventory: sources[{position}] must be an object with a string source_id")
                continue
            by_id[source["source_id"]] = source
        return by_id

    def read_annotation_ids(self, source_id: str) -> set[str] | None:
        """Return the phase (or legacy event) ids of the source's annotation; None when it has none."""
        if source_id not in self.annotation_ids:
            self.annotation_ids[source_id] = self.load_annotation_ids(source_id)
        return self.annotation_ids[source_id]

    def load_annotation_ids(self, source_id: str) -> set[str] | None:
        relative_path = self.by_id[source_id].get("annotation")
        if relative_path is None:
            return None
        if not isinstance(relative_path, str):
            self.problems.append(f"inventory: {source_id}: annotation must be a path or null, got {relative_path!r}")
            return set()
        path = self.directory / relative_path
        annotation = load_json(path, self.problems)
        if annotation is None:
            return set()
        records = annotation.get("phases", annotation.get("events")) if isinstance(annotation, dict) else None
        if not isinstance(records, list):
            self.problems.append(f"{path}: annotation must be an object with a phases or events list")
            return set()
        return {record["id"] for record in records if isinstance(record, dict) and isinstance(record.get("id"), str)}


def check_source(source: dict, label: str, inventory: Inventory, problems: list[str]) -> None:
    """Check a primary source or an alternate against the inventory and its annotation."""
    source_id = source.get("source_id")
    entry = inventory.by_id.get(source_id) if isinstance(source_id, str) else None
    if entry is None:
        problems.append(f"{label}: unknown source {source_id!r}")
        return
    if source.get("path") != entry.get("path"):
        problems.append(
            f"{label}: path {source.get('path')!r} does not match inventory path {entry.get('path')!r} for {source_id}"
        )
    check_evidence_refs(source, source_id, label, inventory, problems)
    times = read_numbers(source, ("source_in", "source_out"), label, problems)
    if times is None:
        return
    source_in, source_out = times
    duration = entry.get("duration_seconds")
    if not is_number(duration):
        problems.append(f"inventory: {source_id}: duration_seconds must be a number, got {duration!r}")
    elif source_in < 0 or source_out <= source_in or source_out > duration + DURATION_TOLERANCE_SECONDS:
        problems.append(f"{label}: invalid range for {source_id}: {source_in}-{source_out}")


def check_evidence_refs(source: dict, source_id: str, label: str, inventory: Inventory, problems: list[str]) -> None:
    references = source.get("evidence_refs")
    if not isinstance(references, list) or not all(isinstance(reference, str) for reference in references):
        problems.append(f"{label}: evidence_refs must be a list of annotation ids, got {references!r}")
        return
    if not references:
        return
    known_ids = inventory.read_annotation_ids(source_id)
    if known_ids is None:
        problems.append(f"{label}: {source_id} has no annotation to hold evidence refs {references}")
        return
    for reference in references:
        if reference not in known_ids:
            problems.append(f"{label}: evidence ref {reference!r} is not in the annotation of {source_id}")


def check_unique_id(record: dict, kind: str, label: str, seen: set[str], problems: list[str]) -> None:
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        problems.append(f"{label}: id must be a non-empty string, got {record_id!r}")
    elif record_id in seen:
        problems.append(f"{label}: {kind} id {record_id!r} is used more than once")
    else:
        seen.add(record_id)


def read_hook_seconds(brief: dict, problems: list[str]) -> float:
    if "hook_seconds" not in brief:
        return DEFAULT_HOOK_SECONDS
    hook_seconds = brief["hook_seconds"]
    if not is_positive_number(hook_seconds):
        problems.append(f"brief: hook_seconds must be a positive number, got {hook_seconds!r}")
        return DEFAULT_HOOK_SECONDS
    return hook_seconds


def check_approval(plan: dict, variant_ids: set[str], problems: list[str]) -> None:
    status = plan.get("approval_status")
    approved_variant = plan.get("approved_variant")
    if status == "approved":
        if not isinstance(approved_variant, str) or approved_variant not in variant_ids:
            problems.append(f"approved_variant must name one of the variants when approved, got {approved_variant!r}")
    elif status == "pending_approval":
        if approved_variant is not None:
            problems.append(f"approved_variant must be null while pending_approval, got {approved_variant!r}")
    else:
        problems.append(f"approval_status must be pending_approval or approved, got {status!r}")


def has_stand_in(beat: dict, label: str, asset_ids: set, gap_ids: set, problems: list[str]) -> bool:
    """A beat without footage must point at a known gap or at a generated asset of its own variant."""
    if "gap_id" not in beat and "asset_id" not in beat:
        problems.append(f"{label}: a beat without a source needs a gap_id or asset_id")
        return False
    valid = True
    if "gap_id" in beat and not is_known_id(beat["gap_id"], gap_ids):
        problems.append(f"{label}: gap_id {beat['gap_id']!r} is not in gaps")
        valid = False
    if "asset_id" in beat and not is_known_id(beat["asset_id"], asset_ids):
        problems.append(f"{label}: asset_id {beat['asset_id']!r} is not in this variant's generated_assets")
        valid = False
    return valid


def check_beat(
    beat: dict, label: str, asset_ids: set, gap_ids: set, inventory: Inventory, problems: list[str]
) -> float | None:
    """Check one beat; return its timeline_out when it is a usable hook (footage or a valid stand-in)."""
    hook_end = None
    timeline = read_numbers(beat, ("timeline_in", "timeline_out"), label, problems)
    if timeline is not None:
        timeline_in, timeline_out = timeline
        if timeline_in >= timeline_out:
            problems.append(f"{label}: timeline_in {timeline_in} must be before timeline_out {timeline_out}")
        elif beat.get("role") == "hook":
            hook_end = timeline_out
    if beat.get("confidence") not in CONFIDENCE_LEVELS:
        problems.append(
            f"{label}: confidence must be one of {', '.join(CONFIDENCE_LEVELS)}, got {beat.get('confidence')!r}"
        )
    approximate = beat.get("source_in_out_is_approximate")
    if not isinstance(approximate, bool):
        problems.append(f"{label}: source_in_out_is_approximate must be true or false, got {approximate!r}")
    source = beat.get("source")
    if isinstance(source, dict):
        check_source(source, f"{label} source", inventory, problems)
    elif source is not None:
        problems.append(f"{label}: source must be an object or null, got {source!r}")
        hook_end = None
    elif not has_stand_in(beat, label, asset_ids, gap_ids, problems):
        hook_end = None
    if "alternates" in beat:
        for position, alternate in enumerate(list_objects(beat, "alternates", label, problems)):
            check_source(alternate, f"{label} alternates[{position}]", inventory, problems)
    return hook_end


def validate(plan: dict, index: dict, inventory_directory: Path) -> list[str]:
    problems: list[str] = []
    inventory = Inventory(index, inventory_directory, problems)

    if plan.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}, got {plan.get('schema_version')!r}")
    evidence_policy = plan.get("evidence_policy")
    if not isinstance(evidence_policy, dict) or evidence_policy.get("mass_reanalysis_run") is not False:
        problems.append("evidence_policy: mass_reanalysis_run must be false")
    brief = plan.get("brief")
    if not isinstance(brief, dict):
        problems.append("brief must be an object")
        brief = {}
    if not is_positive_number(brief.get("fps")):
        problems.append(f"brief: fps must be a positive number, got {brief.get('fps')!r}")
    hook_seconds = read_hook_seconds(brief, problems)
    gap_ids = collect_ids(list_objects(plan, "gaps", "plan", problems))

    variants = list_objects(plan, "variants", "plan", problems)
    if isinstance(plan.get("variants"), list) and not plan["variants"]:
        problems.append("plan: variants must not be empty")
    variant_ids: set[str] = set()
    beat_ids: set[str] = set()
    for variant_position, variant in enumerate(variants):
        variant_label = f"variant {variant.get('id')!r}"
        check_unique_id(variant, "variant", f"variants[{variant_position}]", variant_ids, problems)
        asset_ids = collect_ids(list_objects(variant, "generated_assets", variant_label, problems))
        hook_ends = []
        for position, beat in enumerate(list_objects(variant, "beats", variant_label, problems)):
            label = f"{variant_label} beats[{position}]"
            check_unique_id(beat, "beat", label, beat_ids, problems)
            hook_end = check_beat(beat, label, asset_ids, gap_ids, inventory, problems)
            if hook_end is not None:
                hook_ends.append(hook_end)
        if not any(hook_end <= hook_seconds for hook_end in hook_ends):
            problems.append(f"{variant_label}: hook does not finish by {hook_seconds} seconds")
    check_approval(plan, variant_ids, problems)
    return problems


def main() -> int:
    arguments = parse_arguments()
    problems: list[str] = []
    plan = load_object(arguments.plan, "plan", problems)
    index = load_object(arguments.inventory, "inventory", problems)
    if not problems:
        problems = validate(plan, index, arguments.inventory.parent)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    variants = plan["variants"]
    print(f"VALID: {len(variants)} variants, {sum(len(variant['beats']) for variant in variants)} beats")
    return 0


if __name__ == "__main__":
    sys.exit(main())
