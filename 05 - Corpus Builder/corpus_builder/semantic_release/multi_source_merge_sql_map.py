from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .multi_source_merge_sql_map_artifacts import (
    existing_artifact_paths,
    source_artifact_path,
    target_artifact_path,
)
from .multi_source_merge_sql_map_ids import (
    mapping_by_source_document,
    namespace_colliding_batches,
    source_document_map,
    target_document_id,
)
from .multi_source_merge_sql_map_sources import source_databases, source_document_rows, source_embedding_id


def build_id_map_mappings(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    target_root = Path(str(selection.get("target_artifact_root") or "")).resolve(strict=False)
    existing_target_paths = existing_artifact_paths(target_root)
    mappings: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    artifact_target_paths: dict[tuple[str, str], str] = {}
    for source in source_databases(selection):
        source_database_id = str(source.get("source_database_id") or "")
        if source_database_id in seen_source_ids:
            raise ValueError("source_identity_missing: source_database_id values must be unique.")
        seen_source_ids.add(source_database_id)
        if str(source.get("source_state") or "") == "empty":
            continue
        source_database_path = Path(str(source.get("source_database_path") or "")).resolve(strict=False)
        source_artifact_root = Path(str(source.get("source_artifact_root") or "")).resolve(strict=False)
        for row in source_document_rows(source_database_path):
            mappings.append(
                _mapping_for_source_row(
                    selection,
                    source,
                    row,
                    source_database_id=source_database_id,
                    source_database_path=source_database_path,
                    source_artifact_root=source_artifact_root,
                    existing_target_paths=existing_target_paths,
                    artifact_target_paths=artifact_target_paths,
                )
            )
    return namespace_colliding_batches(mappings)


def _mapping_for_source_row(
    selection: Mapping[str, Any],
    source: Mapping[str, Any],
    row,
    *,
    source_database_id: str,
    source_database_path: Path,
    source_artifact_root: Path,
    existing_target_paths: set[str],
    artifact_target_paths: dict[tuple[str, str], str],
) -> dict[str, Any]:
    source_document_id = str(row["id"])
    artifact_path = source_artifact_path(row, source_artifact_root)
    artifact_key = (source_database_id, artifact_path)
    target_path = artifact_target_paths.get(artifact_key)
    if target_path is None:
        target_path = target_artifact_path(
            source_database_id=source_database_id,
            source_relative_path=artifact_path,
            source_content_hash=str(row["content_hash"] or ""),
            existing_target_paths=existing_target_paths,
        )
        artifact_target_paths[artifact_key] = target_path
        existing_target_paths.add(target_path)
    target_id = target_document_id(
        merge_run_id=str(selection.get("merge_run_id") or ""),
        source_database_id=source_database_id,
        source_document_id=source_document_id,
    )
    return {
        "source_database_id": source_database_id,
        "source_database_path": str(source_database_path),
        "source_record_id": source_document_id,
        "source_document_id": source_document_id,
        "source_original_file_name": str(row["file_name"] or Path(artifact_path).name),
        "source_content_hash": str(row["content_hash"] or ""),
        "source_artifact_path": artifact_path,
        "source_artifact_root": str(source_artifact_root),
        "source_pipeline_batch_id": str(source.get("source_pipeline_batch_id") or source_database_id),
        "source_embedding_id": source_embedding_id(source_database_path, source_document_id),
        "target_record_id": target_id,
        "target_document_id": target_id,
        "target_artifact_path": target_path,
        "target_pipeline_batch_id": "",
        "target_embedding_id": target_id,
        "semantic_release_id": str(source.get("source_semantic_release_id", "")),
        "semantic_release_version": str(source.get("source_semantic_release_version", "")),
        "release_fingerprint": str(source.get("source_release_fingerprint", "")),
        "taxonomy_fingerprint": str(source.get("source_taxonomy_fingerprint") or source.get("source_release_fingerprint") or ""),
        "projection_id": str(row["projection_id"] or source.get("source_projection_id") or ""),
        "projection_fingerprint": str(row["projection_fingerprint"] or source.get("source_projection_fingerprint") or ""),
    }


__all__ = ["build_id_map_mappings", "mapping_by_source_document", "source_document_map"]
