from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.merge import MERGE_ID_MAP_REQUIRED_FIELDS, MergeWorkflowBlocker
from semantic_control_kernel.validation.merge_validation_common import norm_path, require_fields, require_non_empty, stable_payload


def validate_id_map(id_map: Mapping[str, Any]) -> None:
    require_fields(
        id_map,
        (
            "schema_version",
            "merge_run_id",
            "created_at",
            "source_databases",
            "target_database_path",
            "mappings",
            "record_count",
            "map_fingerprint",
        ),
        "kernel.database_merge_id_map.v1",
    )
    mappings = id_map.get("mappings")
    if not isinstance(mappings, list):
        raise ValueError("mappings must be a list.")
    source_paths_by_id = _source_paths_by_id(id_map.get("source_databases"))
    colliding_batches = _colliding_source_batches(mappings)
    for mapping in mappings:
        _validate_mapping(mapping, source_paths_by_id, colliding_batches)
    if int(id_map.get("record_count", -1)) != len(mappings):
        raise ValueError("record_count must equal mappings length.")
    if id_map.get("map_fingerprint") != id_map_fingerprint(id_map):
        raise ValueError("map_fingerprint does not match ID map.")


def id_map_fingerprint(id_map: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in id_map.items() if key != "map_fingerprint"}
    return stable_hash(repr(stable_payload(payload)))


def validate_materialization_refs_preserved(id_map: Mapping[str, Any]) -> MergeWorkflowBlocker | None:
    for mapping in id_map.get("mappings", []):
        if isinstance(mapping, Mapping) and any(not mapping.get(field) for field in MATERIALIZATION_REF_FIELDS):
            return MergeWorkflowBlocker(
                blocker_code="materialization_provenance_missing",
                step_id="merge_database_filled_additive",
                function_or_route="merge_database_filled_additive",
                recovery_state_class="support_only_unrecoverable",
                user_visible_summary="Filled merge cannot preserve record materialization provenance.",
                diagnostics=({"mapping": dict(mapping)},),
            )
    return None


def _source_paths_by_id(source_databases: object) -> dict[str, str]:
    if not isinstance(source_databases, list):
        raise ValueError("source_databases must be a list.")
    return {
        str(item.get("source_database_id", "")): str(item.get("source_database_path", ""))
        for item in source_databases
        if isinstance(item, Mapping) and str(item.get("source_database_id", ""))
    }


def _validate_mapping(mapping: object, source_paths_by_id: Mapping[str, str], colliding_batches: set[str]) -> None:
    if not isinstance(mapping, Mapping):
        raise ValueError("mapping entries must be objects.")
    require_fields(mapping, MERGE_ID_MAP_REQUIRED_FIELDS, "kernel.database_merge_id_map.v1.mappings[]")
    require_non_empty(mapping, _non_empty_id_map_fields(mapping), "kernel.database_merge_id_map.v1.mappings[]")
    source_database_id = str(mapping.get("source_database_id", ""))
    if source_paths_by_id and source_database_id not in source_paths_by_id:
        raise ValueError("kernel.database_merge_id_map.v1.mappings[] source_database_id is not in source_databases.")
    declared_source_path = source_paths_by_id.get(source_database_id, "")
    if declared_source_path and norm_path(declared_source_path) != norm_path(mapping.get("source_database_path")):
        raise ValueError("kernel.database_merge_id_map.v1.mappings[] source_database_path does not match source_databases.")
    source_batch_id = str(mapping.get("source_pipeline_batch_id", ""))
    expected_batch_id = f"{source_database_id}.{source_batch_id}" if source_batch_id in colliding_batches else source_batch_id
    if str(mapping.get("target_pipeline_batch_id", "")) != expected_batch_id:
        raise ValueError("target_pipeline_batch_id does not match Phase 12 batch collision policy.")


def _colliding_source_batches(mappings: Sequence[Any]) -> set[str]:
    batch_sources: dict[str, set[str]] = {}
    for mapping in mappings:
        if isinstance(mapping, Mapping):
            batch_id = str(mapping.get("source_pipeline_batch_id", ""))
            source_database_id = str(mapping.get("source_database_id", ""))
            if batch_id and source_database_id:
                batch_sources.setdefault(batch_id, set()).add(source_database_id)
    return {batch_id for batch_id, source_ids in batch_sources.items() if len(source_ids) > 1}


def _non_empty_id_map_fields(mapping: Mapping[str, Any]) -> tuple[str, ...]:
    fields = [
        "source_database_id",
        "source_database_path",
        "source_record_id",
        "source_document_id",
        "source_original_file_name",
        "source_content_hash",
        "source_pipeline_batch_id",
        "target_record_id",
        "target_document_id",
        "target_pipeline_batch_id",
        "semantic_release_id",
        "semantic_release_version",
        "release_fingerprint",
        "taxonomy_fingerprint",
        "projection_id",
        "projection_fingerprint",
    ]
    if str(mapping.get("source_artifact_path", "")).strip():
        fields.append("target_artifact_path")
    if str(mapping.get("source_embedding_id", "")).strip():
        fields.append("target_embedding_id")
    return tuple(fields)


MATERIALIZATION_REF_FIELDS = (
    "source_pipeline_batch_id",
    "semantic_release_id",
    "semantic_release_version",
    "release_fingerprint",
    "taxonomy_fingerprint",
    "projection_id",
    "projection_fingerprint",
)
