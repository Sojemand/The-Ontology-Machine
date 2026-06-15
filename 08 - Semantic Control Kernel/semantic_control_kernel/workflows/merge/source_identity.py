from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import canonical_path_text, stable_hash
from semantic_control_kernel.types.merge import SourceDatabaseDescriptor


def build_source_descriptor(source: Mapping[str, Any], *, ordinal: int, selection_timestamp: str) -> SourceDatabaseDescriptor:
    durable_id = _optional(source.get("durable_source_database_id") or source.get("source_database_id"))
    source_path = str(source.get("source_database_path", ""))
    artifact_root = _optional(source.get("source_artifact_root"))
    database_fingerprint = str(source.get("source_database_fingerprint") or stable_hash(canonical_path_text(source_path)))
    source_id = durable_id or assign_import_local_source_id(
        ordinal=ordinal,
        source_database_path=source_path,
        source_artifact_root=artifact_root,
        source_database_fingerprint=database_fingerprint,
        selection_timestamp=selection_timestamp,
    )
    return SourceDatabaseDescriptor(
        source_database_id=source_id,
        source_database_path=str(Path(source_path).resolve(strict=False)),
        source_artifact_root=str(Path(artifact_root).resolve(strict=False)) if artifact_root else None,
        source_state=str(source.get("source_state", "")),
        source_semantic_release_id=str(source.get("source_semantic_release_id", "")),
        source_semantic_release_version=str(source.get("source_semantic_release_version", "")),
        source_release_fingerprint=str(source.get("source_release_fingerprint", "")),
        source_database_fingerprint=database_fingerprint,
        source_artifact_tree_fingerprint=str(source.get("source_artifact_tree_fingerprint", "")),
        source_identity_origin="durable_owner_id" if durable_id else "kernel_import_local_id",
        durable_source_database_id=durable_id,
        materialization_refs=tuple(dict(item) for item in source.get("materialization_refs", []) if isinstance(item, Mapping)),
        source_release_ref=dict(source.get("source_release_ref") or {}) if isinstance(source.get("source_release_ref"), Mapping) else {},
    )


def assign_import_local_source_id(
    *,
    ordinal: int,
    source_database_path: str,
    source_artifact_root: str | None,
    source_database_fingerprint: str,
    selection_timestamp: str,
) -> str:
    identity = "|".join(
        (
            canonical_path_text(source_database_path),
            canonical_path_text(source_artifact_root) if source_artifact_root else "",
            source_database_fingerprint,
            selection_timestamp,
        )
    )
    return f"src_{ordinal}_{stable_hash(identity)[:8]}"


def selection_sources_stable(previous_selection: Mapping[str, Any], current_selection: Mapping[str, Any]) -> bool:
    previous = previous_selection.get("source_databases")
    current = current_selection.get("source_databases")
    if not isinstance(previous, list) or not isinstance(current, list) or len(previous) != len(current):
        return False
    for before, after in zip(previous, current):
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            return False
        for field in ("source_database_id", "source_database_path", "source_state", "source_database_fingerprint"):
            if before.get(field) != after.get(field):
                return False
    return True


def _optional(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
