from __future__ import annotations

from typing import Any, Mapping

from .multi_source_merge_types import stable_hash


def target_document_id(*, merge_run_id: str, source_database_id: str, source_document_id: str) -> str:
    return f"mrg_{stable_hash(f'{merge_run_id}:{source_database_id}:{source_document_id}')[:16]}"


def namespace_colliding_batches(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    batch_sources: dict[str, set[str]] = {}
    for mapping in mappings:
        batch_sources.setdefault(str(mapping["source_pipeline_batch_id"]), set()).add(str(mapping["source_database_id"]))
    colliding = {batch_id for batch_id, source_ids in batch_sources.items() if len(source_ids) > 1}
    for mapping in mappings:
        source_batch = str(mapping["source_pipeline_batch_id"])
        mapping["target_pipeline_batch_id"] = (
            f"{mapping['source_database_id']}.{source_batch}" if source_batch in colliding else source_batch
        )
    return mappings


def source_document_map(mappings: list[Mapping[str, Any]], source_database_id: str) -> dict[str, str]:
    return {
        str(item.get("source_document_id") or ""): str(item.get("target_document_id") or "")
        for item in mappings
        if str(item.get("source_database_id") or "") == source_database_id
    }


def mapping_by_source_document(mappings: list[Mapping[str, Any]], source_database_id: str) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("source_document_id") or ""): dict(item)
        for item in mappings
        if str(item.get("source_database_id") or "") == source_database_id
    }
