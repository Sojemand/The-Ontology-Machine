from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ..semantic_release.multi_source_merge_types import path_hash
from .manifest_reader import read_json


JOURNAL_SCHEMA_VERSION = "kernel.cleanup_reingest_journal.v1"


def _cleanup_plan_path(artifact_root: Path, cleanup_plan_id: str) -> Path:
    return artifact_root / "Documents" / "logs" / "pipeline_batches" / "cleanup_plans" / f"{cleanup_plan_id}.json"


def _cleanup_journal_path(artifact_root: Path, plan: Mapping[str, Any]) -> Path:
    source_ref = _mapping(plan.get("source_manifest_ref"))
    pipeline_batch_id = str(source_ref.get("pipeline_batch_id") or "")
    if pipeline_batch_id:
        return artifact_root / "Documents" / "logs" / "pipeline_batches" / pipeline_batch_id / "cleanup_journal.json"
    sample_ref = _mapping(plan.get("sample_selection_ref"))
    sample_selection_id = str(sample_ref.get("sample_selection_id") or "selection_cleanup")
    return artifact_root / "Documents" / "logs" / "pipeline_batches" / "selections" / sample_selection_id / "cleanup_journal.json"


def _load_json_ref(
    value: Mapping[str, Any],
    artifact_root: Path,
    *,
    default_path: Path | None = None,
) -> dict[str, Any]:
    artifact_path = str(value.get("artifact_path") or "")
    if artifact_path:
        path = (artifact_root / artifact_path).resolve(strict=False)
    elif default_path is not None and str(default_path):
        path = default_path.resolve(strict=False)
    else:
        raise ValueError("artifact_path is required.")
    try:
        path.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError("artifact ref escapes the active artifact tree.") from exc
    return read_json(path)


def _resolve_database_path(
    payload: Mapping[str, Any],
    plan: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    artifact_root: Path,
) -> Path:
    for candidate in (
        _mapping(payload.get("database_ref")),
        _mapping(payload.get("active_database")),
        _mapping(plan.get("database_ref")),
        _mapping(source_manifest.get("active_database")),
    ):
        database_path = str(candidate.get("database_path") or "").strip()
        if database_path:
            resolved = Path(database_path).resolve(strict=False)
            _validate_database_path_hash(resolved, payload, source_manifest)
            return resolved
    expected_hash = str(
        _mapping(payload.get("database_ref")).get("database_path_hash")
        or _mapping(source_manifest.get("active_database")).get("database_path_hash")
        or _mapping(payload.get("target_identity")).get("database_path_hash")
        or ""
    )
    for candidate in (artifact_root / "Corpus" / "corpus.db", artifact_root / "Corpus" / "active.db"):
        if candidate.exists() and (not expected_hash or path_hash(candidate) == expected_hash):
            resolved = candidate.resolve(strict=False)
            _validate_database_path_hash(resolved, payload, source_manifest)
            return resolved
    raise ValueError("database_missing: cleanup requires a concrete active database path.")


def _validate_database_path_hash(database_path: Path, payload: Mapping[str, Any], source_manifest: Mapping[str, Any]) -> None:
    expected_hashes = {
        str(value or "")
        for value in (
            _mapping(payload.get("database_ref")).get("database_path_hash"),
            _mapping(payload.get("target_identity")).get("database_path_hash"),
            _mapping(source_manifest.get("active_database")).get("database_path_hash"),
        )
        if value
    }
    actual = path_hash(database_path)
    if expected_hashes and actual not in expected_hashes:
        raise ValueError("target_identity_changed: cleanup database_path_hash does not match the active target.")


def _validate_target_identity(artifact_root: Path, target_identity: Mapping[str, Any]) -> None:
    expected_hash = str(target_identity.get("artifact_root_path_hash") or "")
    if expected_hash and expected_hash != path_hash(artifact_root):
        raise ValueError("target_identity_changed: artifact_root_path_hash does not match the active artifact root.")


def _mapping(payload: object, key: str | None = None) -> dict[str, Any]:
    value = payload if key is None else payload.get(key) if isinstance(payload, Mapping) else None
    return dict(value) if isinstance(value, Mapping) else {}
