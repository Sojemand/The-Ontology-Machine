from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .multi_source_merge_types import path_hash


def classify_sources(source_databases: list[Mapping[str, Any]]) -> tuple[str, bool]:
    states = {str(item.get("source_state", "")) for item in source_databases}
    if states == {"empty"}:
        return "empty", False
    if states <= {"empty", "filled"} and "filled" in states:
        return "filled", states != {"filled"}
    return "unknown", True


def validate_merge_selection(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    merge_run_id = str(selection.get("merge_run_id") or "").strip()
    if not merge_run_id:
        raise ValueError("merge_run_id is required.")
    target_artifact_root = str(selection.get("target_artifact_root") or "").strip()
    if not target_artifact_root:
        raise ValueError("target_artifact_root is required.")
    target_database_path = str(selection.get("target_database_path") or "").strip()
    if not target_database_path:
        raise ValueError("target_database_path is required.")
    sources = [dict(item) for item in selection.get("source_databases", []) if isinstance(item, Mapping)]
    if len(sources) < 2:
        raise ValueError("fewer_than_two_sources: multi-source merge requires at least two sources.")
    source_ids: set[str] = set()
    for source in sources:
        for field in (
            "source_database_id",
            "source_database_path",
            "source_artifact_root",
            "source_state",
            "source_semantic_release_id",
            "source_semantic_release_version",
            "source_release_fingerprint",
        ):
            if source.get(field) in (None, "", [], {}):
                raise ValueError(f"source_identity_missing: {field} is required for multi-source merge.")
        source_database_id = str(source.get("source_database_id") or "")
        if source_database_id in source_ids:
            raise ValueError("source_identity_missing: source_database_id values must be unique.")
        source_ids.add(source_database_id)
    source_class, _mixed = classify_sources(sources)
    if source_class == "unknown":
        raise ValueError("source_state_unknown: source_state values must be empty or filled.")
    return sources


def validate_target_identity(selection: Mapping[str, Any], target_identity: Mapping[str, Any]) -> None:
    expected_merge_run_id = str(selection.get("merge_run_id") or "")
    actual_merge_run_id = str(target_identity.get("merge_run_id") or "")
    if actual_merge_run_id and actual_merge_run_id != expected_merge_run_id:
        raise ValueError("target_identity_changed: merge_run_id does not match the requested merge selection.")
    expected_target_hash = path_hash(str(selection.get("target_database_path") or ""))
    actual_target_hash = str(target_identity.get("target_database_path_hash") or "")
    if actual_target_hash and actual_target_hash != expected_target_hash:
        raise ValueError("target_identity_changed: target_database_path_hash does not match the requested merge target.")
    expected_source_ids = [str(item.get("source_database_id") or "") for item in selection.get("source_databases", []) if isinstance(item, Mapping)]
    actual_source_ids = target_identity.get("source_database_ids")
    if isinstance(actual_source_ids, list) and actual_source_ids != expected_source_ids:
        raise ValueError("target_identity_changed: source_database_ids do not match the requested merge selection.")


def validate_artifact_path_within_root(target_artifact_root: str | Path, artifact_path: str) -> Path:
    root = Path(target_artifact_root).resolve(strict=False)
    candidate = (root / artifact_path).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("artifact ref escapes the active target artifact root.") from exc
    return candidate
