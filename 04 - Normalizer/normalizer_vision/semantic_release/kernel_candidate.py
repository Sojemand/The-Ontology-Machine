from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_CUSTOM_RELEASE_VERSION = "custom.v1"


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compile_candidate(
    *,
    taxonomy_ref: Mapping[str, Any],
    projection_refs: Sequence[Mapping[str, Any]],
    runtime_locale: str,
    semantic_release_folder: str,
    release_identity_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    seed = stable_hash(repr((dict(taxonomy_ref), [dict(item) for item in projection_refs], runtime_locale, dict(release_identity_policy or {}))))
    release_id = str((release_identity_policy or {}).get("release_id") or f"release_{seed[:12]}")
    release_version = str((release_identity_policy or {}).get("release_version") or DEFAULT_CUSTOM_RELEASE_VERSION)
    return {
        "semantic_release_candidate_ref": {"artifact_path": str((Path(semantic_release_folder) / "releases" / release_id / "candidate.json").as_posix())},
        "semantic_release_id": release_id,
        "semantic_release_version": release_version,
        "release_fingerprint": stable_hash(f"release:{seed}"),
        "taxonomy_fingerprint": str(taxonomy_ref.get("taxonomy_fingerprint", "")),
        "projection_fingerprints": {
            str(item.get("projection_id", projection_id)): str(item.get("projection_fingerprint", ""))
            for projection_id, item in enumerate(projection_refs, start=1)
            if isinstance(item, Mapping)
        },
        "package_paths": [str((Path(semantic_release_folder) / "releases" / release_id).as_posix())],
        "release_ref": {
            "release_id": release_id,
            "release_version": release_version,
            "release_fingerprint": stable_hash(f"release:{seed}"),
            "taxonomy_ref": dict(taxonomy_ref),
            "projection_refs": [dict(item) for item in projection_refs],
            "runtime_locale": runtime_locale,
        },
    }
