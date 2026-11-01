# edit_plan.json, schema 2

`scripts/validate_edit_plan.py PLAN INDEX` checks everything stated here
except the truth of the descriptions.

```json
{
  "schema_version": 2,
  "approval_status": "pending_approval",
  "approved_variant": null,
  "inventory_path": "sheets/index.json",
  "brief": {"logline": "...", "aspect_ratio": "9:16", "target_duration_seconds": 30, "fps": 30, "hook_seconds": 3.0},
  "evidence_policy": {"draft_annotations_allowed": true, "mass_reanalysis_run": false},
  "story_risks": ["..."],
  "variants": [{
    "id": "A",
    "title": "...",
    "duration_seconds": 30,
    "beats": [{
      "id": "A01",
      "timeline_in": 0,
      "timeline_out": 2.4,
      "role": "hook",
      "source": {"source_id": "...", "path": "...", "source_in": 16.2, "source_out": 18.0, "evidence_refs": ["P03"]},
      "source_in_out_is_approximate": true,
      "visual": "...",
      "title": "...",
      "audio": {"dialogue": null, "music": "...", "sfx": ["..."]},
      "confidence": "supported_but_unproven",
      "alternates": [{"source_id": "...", "path": "...", "source_in": 3.0, "source_out": 4.5, "evidence_refs": ["P01"]}]
    }],
    "generated_assets": [{"id": "G1", "kind": "title", "description": "..."}]
  }],
  "gaps": [{"id": "GAP1", "role": "reveal", "reason": "no take shows the note legibly"}],
  "approval_questions": ["..."]
}
```

- `approval_status` is `pending_approval` with `approved_variant: null` until
  the user chooses; then `approved` with the chosen variant's `id`.
- `brief.fps` is the timeline frame rate the assembly converts seconds with;
  `hook_seconds` defaults to 3.0.
- Beat `id`s are unique across the plan and stay the same through assembly
  and its report.
- `source` and every alternate name an inventory `source_id` and its exact
  `path`, a range inside the source's duration, and `evidence_refs` that are
  phase ids (or legacy event ids) of that source's annotation.
- A beat with `source: null` names a `gap_id` from `gaps` or an `asset_id`
  from its variant's `generated_assets`.
- `confidence` is `confirmed`, `supported_but_unproven` or
  `missing_or_unverified`.
- Each variant has a `hook` beat ending by `hook_seconds`; a generated hook
  counts.
- Times are seconds, `timeline_in < timeline_out`, `source_in < source_out`.
- `evidence_policy.mass_reanalysis_run` is `false`: planning works from the
  inventory and never re-analyses the whole collection.
