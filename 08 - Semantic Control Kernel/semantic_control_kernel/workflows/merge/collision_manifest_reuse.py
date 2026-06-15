from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.validation.merge_validation import validate_collision_manifest


def reuse_existing_manifest(manifest_path: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(manifest_path)
    if not path.is_file():
        return dict(manifest)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(manifest)
    if not isinstance(existing, Mapping):
        return dict(manifest)
    try:
        validate_collision_manifest(existing)
    except ValueError:
        return dict(manifest)
    if _manifest_identity(existing) != _manifest_identity(manifest):
        return dict(manifest)
    if _source_database_ids(existing) != _source_database_ids(manifest):
        return dict(manifest)
    if _collision_fingerprints(existing) != _collision_fingerprints(manifest):
        return dict(manifest)
    return dict(existing)


def _manifest_identity(manifest: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(manifest.get("merge_run_id", "")),
        str(manifest.get("merge_route", "")),
        str(manifest.get("target_artifact_root", "")),
        str(manifest.get("target_database_path", "")),
    )


def _source_database_ids(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    source_databases = manifest.get("source_databases", [])
    if not isinstance(source_databases, list):
        return ()
    return tuple(
        sorted(
            str(item.get("source_database_id", ""))
            for item in source_databases
            if isinstance(item, Mapping) and str(item.get("source_database_id", ""))
        )
    )


def _collision_fingerprints(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    collisions = manifest.get("collisions", [])
    if not isinstance(collisions, list):
        return ()
    fingerprints: list[str] = []
    for item in collisions:
        if not isinstance(item, Mapping):
            continue
        fingerprints.append(
            stable_hash(
                "|".join(
                    (
                        str(item.get("collision_id", "")),
                        str(item.get("collision_class", "")),
                        repr(sorted(str(ref.get("source_database_id", "")) for ref in item.get("source_refs", []) if isinstance(ref, Mapping))),
                    )
                )
            )
        )
    return tuple(sorted(fingerprints))
