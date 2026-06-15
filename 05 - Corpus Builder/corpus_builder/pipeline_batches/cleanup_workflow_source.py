from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .cleanup_workflow_paths import _mapping
from .manifest_reader import read_json


def _load_source_manifest(plan: Mapping[str, Any], artifact_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    cleanup_scope = str(plan.get("cleanup_scope") or "")
    if cleanup_scope == "selected_batch":
        source_ref = _mapping(plan.get("source_manifest_ref"))
        pipeline_batch_id = str(source_ref.get("pipeline_batch_id") or "")
        manifest_path = artifact_root / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "pipeline_batch_manifest.json"
        manifest = read_json(manifest_path)
        if source_ref.get("manifest_fingerprint") and source_ref["manifest_fingerprint"] != manifest.get("manifest_fingerprint"):
            raise ValueError("partial_pipeline_run: cleanup plan source manifest fingerprint is stale.")
        return manifest, source_ref
    source_ref = _mapping(plan.get("sample_selection_ref"))
    sample_selection_id = str(source_ref.get("sample_selection_id") or "")
    manifest_path = artifact_root / "Documents" / "logs" / "pipeline_batches" / "selections" / sample_selection_id / "sample_selection_manifest.json"
    manifest = read_json(manifest_path)
    if source_ref.get("selection_fingerprint") and source_ref["selection_fingerprint"] != manifest.get("selection_fingerprint"):
        raise ValueError("partial_pipeline_run: cleanup plan sample selection fingerprint is stale.")
    return manifest, source_ref


def _removed_artifact_refs(
    plan: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    artifact_root: Path,
) -> list[dict[str, Any]]:
    derived_paths = {
        str(item.get("artifact_path") or "").replace("\\", "/")
        for item in _source_artifact_refs(source_manifest)
        if isinstance(item, Mapping) and item.get("artifact_path")
    }
    requested = [dict(item) for item in plan.get("affected_artifacts", []) if isinstance(item, Mapping)]
    if requested:
        requested_paths = {
            str(item.get("artifact_path") or "").replace("\\", "/")
            for item in requested
            if item.get("artifact_path")
        }
        if derived_paths and not requested_paths.issubset(derived_paths):
            raise ValueError("records_not_isolated: cleanup plan artifact refs broaden beyond the isolated source manifest.")
        refs = requested
    else:
        refs = _source_artifact_refs(source_manifest)
    for item in refs:
        artifact_path = str(item.get("artifact_path") or "")
        if not artifact_path:
            raise ValueError("records_not_isolated: cleanup artifact refs must include artifact_path.")
        normalized = artifact_path.replace("\\", "/")
        if normalized.startswith(("Documents/originals/", "Documents/logs/", "Input/", "Semantic Release/")):
            raise ValueError("records_not_isolated: cleanup must not remove originals, logs, Input files or semantic releases.")
        resolved = artifact_root / normalized
        try:
            resolved.relative_to(artifact_root)
        except ValueError as exc:
            raise ValueError("records_not_isolated: cleanup artifact ref escapes the active artifact tree.") from exc
    return refs


def _preserved_original_refs(source_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    preserved: list[dict[str, Any]] = []
    for record in _source_records(source_manifest):
        original_ref = ""
        if isinstance(record.get("original_ref"), str):
            original_ref = str(record["original_ref"])
        elif isinstance(record.get("source_path"), str):
            original_ref = str(record["source_path"])
        if original_ref:
            preserved.append({"original_ref": original_ref, "preserved": True})
    return preserved


def _source_records(source_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = source_manifest.get("materialized_records")
    if isinstance(records, list) and records:
        return [dict(item) for item in records if isinstance(item, Mapping)]
    selected = source_manifest.get("selected_records")
    if isinstance(selected, list):
        return [dict(item) for item in selected if isinstance(item, Mapping)]
    return []


def _source_artifact_refs(source_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for record in _source_records(source_manifest):
        artifact_refs = record.get("artifact_refs")
        if isinstance(artifact_refs, list):
            refs.extend(dict(item) for item in artifact_refs if isinstance(item, Mapping))
    return refs


def _source_record_count(source_manifest: Mapping[str, Any]) -> int:
    return len(_source_records(source_manifest))
