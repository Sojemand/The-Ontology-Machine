from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.policy.batch_policy import PIPELINE_BATCH_ID_RE
from phase12_frozen_inventory import (
    PIPELINE_BATCH_PLACEHOLDER,
    PIPELINE_BATCH_RE,
    RESET_MANIFEST_PLACEHOLDER,
    RESET_MANIFEST_RE,
)

def _artifact_path_map(root: Path) -> dict[str, str]:
    path_map: dict[str, str] = {}
    if not root.exists():
        return path_map
    for path in root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            path_map[rel] = _normalize_runtime_relpath(rel)
    return path_map

def _normalize_runtime_relpath(relative_path: str) -> str:
    relative_path = PIPELINE_BATCH_RE.sub(PIPELINE_BATCH_PLACEHOLDER, relative_path)
    return RESET_MANIFEST_RE.sub(RESET_MANIFEST_PLACEHOLDER, relative_path)

def _artifact_json_contracts(root: Path, path_map: Mapping[str, str]) -> dict[str, Any]:
    contracts = {}
    for actual_rel, normalized_rel in sorted(path_map.items(), key=lambda item: item[1]):
        path = root / actual_rel
        if path.suffix != ".json":
            continue
        contracts[normalized_rel] = _json_contract_summary(
            normalized_rel,
            json.loads(path.read_text(encoding="utf-8")),
        )
    return contracts

def _json_contract_summary(relative_path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if relative_path.endswith("/merge_selection.json"):
        sources = [dict(item) for item in payload.get("source_databases", []) if isinstance(item, Mapping)]
        return {
            "merge_route": payload.get("merge_route"),
            "projection_merge_mode": payload.get("projection_merge_mode"),
            "schema_version": payload.get("schema_version"),
            "source_database_ids": [item.get("source_database_id") for item in sources],
            "source_identity_origins": [item.get("source_identity_origin") for item in sources],
            "source_states": [item.get("source_state") for item in sources],
            "target_database_name": Path(str(payload.get("target_database_path", ""))).name,
        }
    if relative_path.endswith("/merge_collision_manifest.json"):
        return {
            "collision_count": len(payload.get("collisions") or []),
            "duplicate_policy": payload.get("duplicate_policy"),
            "merge_route": payload.get("merge_route"),
            "manifest_revision": payload.get("manifest_revision"),
            "resolution_summary": dict(payload.get("resolution_summary") or {}),
            "schema_version": payload.get("schema_version"),
            "source_database_ids": [
                item.get("source_database_id")
                for item in payload.get("source_databases", [])
                if isinstance(item, Mapping)
            ],
        }
    if relative_path.endswith("/merge_id_map.json"):
        mappings = [dict(item) for item in payload.get("mappings", []) if isinstance(item, Mapping)]
        return {
            "record_count": payload.get("record_count"),
            "schema_version": payload.get("schema_version"),
            "source_database_ids": sorted({str(item.get("source_database_id")) for item in mappings}),
            "target_artifact_paths": [item.get("target_artifact_path") for item in mappings],
            "target_pipeline_batch_ids": [item.get("target_pipeline_batch_id") for item in mappings],
        }
    if relative_path.endswith("/release.json"):
        taxonomy_ref = payload.get("taxonomy_ref") if isinstance(payload.get("taxonomy_ref"), Mapping) else {}
        projection_refs = payload.get("projection_refs") if isinstance(payload.get("projection_refs"), list) else []
        return {
            "projection_count": len(projection_refs),
            "projection_ids": [item.get("projection_id") for item in projection_refs if isinstance(item, Mapping)],
            "release_fingerprint": payload.get("release_fingerprint"),
            "release_id": payload.get("release_id"),
            "release_version": payload.get("release_version"),
            "runtime_locale": payload.get("runtime_locale"),
            "taxonomy_id": taxonomy_ref.get("taxonomy_id"),
        }
    if relative_path.endswith("/rebuild_manifest.json"):
        return {
            "adapter_call_ref_count": len(payload.get("adapter_call_refs") or []),
            "embedding_policy": payload.get("embedding_policy"),
            "embedding_result": payload.get("embedding_result"),
            "loaded_release_fingerprint": payload.get("loaded_release_fingerprint"),
            "loaded_semantic_release_id": payload.get("loaded_semantic_release_id"),
            "loaded_semantic_release_version": payload.get("loaded_semantic_release_version"),
            "record_count": payload.get("record_count"),
            "rebuild_run_id": payload.get("rebuild_run_id"),
            "schema_version": payload.get("schema_version"),
            "target_database_name": Path(str(payload.get("target_database_path", ""))).name,
            "workflow_run_id": payload.get("workflow_run_id"),
        }
    if relative_path.endswith("/pending_pipeline_batch_manifest.json"):
        return {
            "active_projection_count": len(payload.get("active_projections") or []),
            "batch_kind": payload.get("batch_kind"),
            "created_by_workflow": payload.get("created_by_workflow"),
            "input_count": len(payload.get("input_files") or []),
            "pending_status": payload.get("pending_status"),
            "pipeline_batch_id_is_valid": _valid_pipeline_batch_id(payload.get("pipeline_batch_id")),
            "schema_version": payload.get("schema_version"),
            "workflow_run_id": payload.get("workflow_run_id"),
        }
    if relative_path.endswith("/pipeline_batch_manifest.json"):
        counts = payload.get("record_counts") if isinstance(payload.get("record_counts"), Mapping) else {}
        return {
            "batch_kind": payload.get("batch_kind"),
            "batch_status": payload.get("batch_status"),
            "cleanup_scope": dict(payload.get("cleanup_eligibility") or {}).get("cleanup_scope"),
            "input_count": len(payload.get("input_files") or []),
            "materialized_record_count": len(payload.get("materialized_records") or []),
            "pipeline_batch_id_is_valid": _valid_pipeline_batch_id(payload.get("pipeline_batch_id")),
            "record_counts": {key: counts.get(key) for key in sorted(counts)},
            "schema_version": payload.get("schema_version"),
            "workflow_run_id": payload.get("workflow_run_id"),
        }
    if relative_path.endswith("/correlation_report.json"):
        return {
            "correlation_status": payload.get("correlation_status"),
            "manifest_eligible": payload.get("manifest_eligible"),
            "mismatch_codes": [
                item.get("code")
                for item in payload.get("mismatch_diagnostics", [])
                if isinstance(item, Mapping)
            ],
            "pipeline_batch_id_is_valid": _valid_pipeline_batch_id(payload.get("pipeline_batch_id")),
            "schema_version": payload.get("schema_version"),
            "workflow_run_id": payload.get("workflow_run_id"),
        }
    if relative_path.endswith(f"/{RESET_MANIFEST_PLACEHOLDER}"):
        return {
            "empty_state_proven": payload.get("empty_state_proven"),
            "post_reset_semantic_release_state": payload.get("post_reset_semantic_release_state"),
            "preserved_release_id": dict(payload.get("preserved_release_ref") or {}).get("semantic_release_id"),
            "prior_semantic_release_state": payload.get("prior_semantic_release_state"),
            "schema_version": payload.get("schema_version"),
            "superseded_batch_ref_count": len(payload.get("superseded_batch_refs") or []),
            "workflow_run_id": payload.get("workflow_run_id"),
        }
    return {"json_keys": sorted(payload.keys())}

def _valid_pipeline_batch_id(value: object) -> bool:
    return isinstance(value, str) and bool(PIPELINE_BATCH_ID_RE.match(value))
