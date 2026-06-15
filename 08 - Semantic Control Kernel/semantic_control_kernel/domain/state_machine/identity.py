from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from semantic_control_kernel.domain.state_machine.models import TargetIdentity, TargetSelector
from semantic_control_kernel.repository.paths import path_hash, stable_hash


PROMPT_LIKE_KEYS = {
    "agent_message",
    "chat_message",
    "freeform_prompt",
    "prompt",
    "prompt_text",
    "user_message",
    "user_prompt",
}


def build_target_identity(target_selector: TargetSelector | Mapping[str, Any], *, created_from: str = "target_selector") -> TargetIdentity:
    selector = target_selector.to_dict() if isinstance(target_selector, TargetSelector) else dict(target_selector)
    database_path_hash = str(selector.get("database_path_hash") or _hash_path(selector.get("database_path")))
    artifact_root_path_hash = str(selector.get("artifact_root_path_hash") or _hash_path(selector.get("artifact_root_path")))
    release_fingerprint = _first_text(selector, "release_fingerprint", "semantic_release_fingerprint")
    release_id = _first_text(selector, "release_id", "semantic_release_id")
    release_version = _first_text(selector, "release_version", "semantic_release_version")
    semantic_release_identity_hash = _semantic_release_identity_hash(release_id, release_version, release_fingerprint)
    projection_set_hash = _projection_set_hash(_projection_fingerprints(selector))
    source_database_set_hash = _source_database_set_hash(_source_database_ids(selector))
    database_id = _first_text(selector, "database_id")
    if not database_id and database_path_hash:
        database_id = f"dbpath:{database_path_hash}"
    lock_scope = str(selector.get("lock_scope") or _default_lock_scope(selector, database_path_hash, artifact_root_path_hash))
    basis = {
        "artifact_root_path_hash": artifact_root_path_hash,
        "database_id": database_id or "",
        "database_path_hash": database_path_hash,
        "lock_scope": lock_scope,
        "pipeline_batch_id": _first_text(selector, "pipeline_batch_id") or "",
        "projection_set_hash": projection_set_hash or "",
        "release_fingerprint": release_fingerprint or "",
        "semantic_release_identity_hash": semantic_release_identity_hash or "",
        "source_database_set_hash": source_database_set_hash or "",
        "taxonomy_fingerprint": _first_text(selector, "taxonomy_fingerprint") or "",
    }
    target_hash = str(selector.get("target_hash") or stable_hash(json.dumps(basis, sort_keys=True, separators=(",", ":"))))
    return TargetIdentity(
        database_path_hash=database_path_hash,
        artifact_root_path_hash=artifact_root_path_hash,
        lock_scope=lock_scope,
        target_hash=target_hash,
        created_from=created_from,
        database_id=database_id,
        release_fingerprint=release_fingerprint,
        semantic_release_identity_hash=semantic_release_identity_hash,
        taxonomy_fingerprint=_first_text(selector, "taxonomy_fingerprint"),
        projection_set_hash=projection_set_hash,
        pipeline_batch_id=_first_text(selector, "pipeline_batch_id"),
        source_database_set_hash=source_database_set_hash,
    )


def semantic_release_identity_hash(release_id: str, release_version: str, release_fingerprint: str) -> str:
    return stable_hash("|".join((release_id, release_version, release_fingerprint)))


def projection_set_hash(projection_fingerprints: Iterable[str]) -> str:
    return stable_hash("|".join(sorted(str(item) for item in projection_fingerprints if item)))


def source_database_set_hash(source_database_ids: Iterable[str]) -> str:
    return stable_hash("|".join(sorted(str(item) for item in source_database_ids if item)))


def target_hash_input_preview(target_selector: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in target_selector.items() if key not in PROMPT_LIKE_KEYS}


def _hash_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return path_hash(value)


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _semantic_release_identity_hash(release_id: str | None, release_version: str | None, release_fingerprint: str | None) -> str | None:
    if not any((release_id, release_version, release_fingerprint)):
        return None
    return semantic_release_identity_hash(release_id or "", release_version or "", release_fingerprint or "")


def _projection_set_hash(values: Iterable[str]) -> str | None:
    items = tuple(str(item) for item in values if item)
    return projection_set_hash(items) if items else None


def _source_database_set_hash(values: Iterable[str]) -> str | None:
    items = tuple(str(item) for item in values if item)
    return source_database_set_hash(items) if items else None


def _projection_fingerprints(selector: Mapping[str, Any]) -> tuple[str, ...]:
    raw = selector.get("projection_fingerprints")
    if isinstance(raw, list):
        return tuple(str(item) for item in raw)
    active = selector.get("active_projections")
    if isinstance(active, list):
        values = []
        for item in active:
            if isinstance(item, Mapping) and isinstance(item.get("projection_fingerprint"), str):
                values.append(item["projection_fingerprint"])
        return tuple(values)
    return ()


def _source_database_ids(selector: Mapping[str, Any]) -> tuple[str, ...]:
    for key in ("source_database_ids", "selected_source_database_ids"):
        raw = selector.get(key)
        if isinstance(raw, list):
            return tuple(str(item) for item in raw)
    raw_sources = selector.get("source_databases")
    if isinstance(raw_sources, list):
        values = []
        for item in raw_sources:
            if isinstance(item, Mapping):
                values.append(str(item.get("database_id") or item.get("database_path") or ""))
            else:
                values.append(str(item))
        return tuple(value for value in values if value)
    return ()


def _default_lock_scope(selector: Mapping[str, Any], database_path_hash: str, artifact_root_path_hash: str) -> str:
    if _source_database_ids(selector):
        return "merge"
    if database_path_hash:
        return "database"
    if artifact_root_path_hash:
        return "artifact_tree"
    return "target"
