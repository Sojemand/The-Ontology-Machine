from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash, utc_iso
from semantic_control_kernel.types.merge import DatabaseMergeIdMap, MERGE_ID_MAP_REQUIRED_FIELDS
from semantic_control_kernel.validation.merge_validation import id_map_fingerprint, validate_id_map


def build_id_map(
    *,
    merge_run_id: str,
    source_databases: Sequence[Mapping[str, Any]],
    target_database_path: str,
    mappings: Sequence[Mapping[str, Any]],
) -> DatabaseMergeIdMap:
    normalized = normalize_mappings(mappings)
    payload = {
        "schema_version": DatabaseMergeIdMap.SCHEMA_VERSION,
        "created_at": utc_iso(),
        "map_fingerprint": "",
        "mappings": normalized,
        "merge_run_id": merge_run_id,
        "record_count": len(normalized),
        "source_databases": [dict(item) for item in source_databases],
        "target_database_path": target_database_path,
    }
    payload["map_fingerprint"] = id_map_fingerprint(payload)
    validate_id_map(payload)
    return DatabaseMergeIdMap(payload)


def normalize_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    payload = {field: mapping.get(field, "") for field in MERGE_ID_MAP_REQUIRED_FIELDS}
    if not payload["target_pipeline_batch_id"]:
        payload["target_pipeline_batch_id"] = target_pipeline_batch_id(
            source_database_id=str(payload["source_database_id"]),
            source_pipeline_batch_id=str(payload["source_pipeline_batch_id"]),
            collides=bool(mapping.get("pipeline_batch_collision")),
        )
    return payload


def normalize_mappings(mappings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [normalize_mapping(mapping) for mapping in mappings]
    colliding_batches = _colliding_source_batches(normalized)
    for mapping in normalized:
        source_batch_id = str(mapping["source_pipeline_batch_id"])
        mapping["target_pipeline_batch_id"] = target_pipeline_batch_id(
            source_database_id=str(mapping["source_database_id"]),
            source_pipeline_batch_id=source_batch_id,
            collides=source_batch_id in colliding_batches,
        )
    return normalized


def target_pipeline_batch_id(*, source_database_id: str, source_pipeline_batch_id: str, collides: bool) -> str:
    if not collides:
        return source_pipeline_batch_id
    return f"{source_database_id}.{source_pipeline_batch_id}"


def append_id_mappings(id_map: Mapping[str, Any], mappings: Sequence[Mapping[str, Any]]) -> DatabaseMergeIdMap:
    payload = deepcopy(dict(id_map))
    existing = [dict(item) for item in payload.get("mappings", []) if isinstance(item, Mapping)]
    existing.extend(dict(item) for item in mappings)
    payload["mappings"] = normalize_mappings(existing)
    payload["record_count"] = len(existing)
    payload["map_fingerprint"] = ""
    payload["map_fingerprint"] = id_map_fingerprint(payload)
    validate_id_map(payload)
    return DatabaseMergeIdMap(payload)


def deterministic_target_id(*parts: object) -> str:
    return f"tgt_{stable_hash(repr(parts))[:12]}"


def _colliding_source_batches(mappings: Sequence[Mapping[str, Any]]) -> set[str]:
    batch_sources: dict[str, set[str]] = {}
    for mapping in mappings:
        batch_id = str(mapping.get("source_pipeline_batch_id", ""))
        source_database_id = str(mapping.get("source_database_id", ""))
        if not batch_id or not source_database_id:
            continue
        batch_sources.setdefault(batch_id, set()).add(source_database_id)
    return {batch_id for batch_id, source_ids in batch_sources.items() if len(source_ids) > 1}
