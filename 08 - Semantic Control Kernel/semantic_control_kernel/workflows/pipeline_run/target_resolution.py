from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash, stable_hash
from semantic_control_kernel.types.batches import FILLED_DATABASE, PipelineRunTarget


def target_from_active_release(
    *,
    workflow_run_id: str,
    artifact_root: str | Path,
    target_database_path: str | Path,
    loaded_release: Mapping[str, Any],
) -> PipelineRunTarget:
    root = Path(artifact_root).resolve(strict=False)
    db_path = Path(target_database_path).resolve(strict=False)
    release = dict(loaded_release.get("release") or {})
    status = dict(loaded_release.get("status") or {})
    active_snapshot = dict(loaded_release.get("active_snapshot") or {})
    active_release_ref = _active_release_ref(loaded_release, release)
    taxonomy_ref = _taxonomy_ref(release, active_release_ref)
    projection_refs = _projection_refs(release)
    state_snapshot_id = str(
        active_snapshot.get("snapshot_id")
        or status.get("active_snapshot_id")
        or stable_hash(f"{path_hash(db_path)}:{active_release_ref.get('release_fingerprint', '')}")
    )
    artifact_root_hash = path_hash(root)
    database_hash = path_hash(db_path)
    return PipelineRunTarget(
        workflow_run_id=workflow_run_id,
        database_path=str(db_path),
        database_path_hash=database_hash,
        database_id=str(status.get("database_id") or f"db:{database_hash}"),
        database_fingerprint=_file_fingerprint(db_path),
        artifact_root_path=str(root),
        artifact_root_path_hash=artifact_root_hash,
        artifact_root_fingerprint=_path_fingerprint(root),
        input_path=str(root / "Input"),
        documents_path=str(root / "Documents"),
        corpus_path=str(root / "Corpus"),
        semantic_release_path=str(root / "Semantic Release"),
        database_emptiness=FILLED_DATABASE,
        semantic_release_state="semantic_release_active",
        active_release_ref=active_release_ref,
        taxonomy_ref=taxonomy_ref,
        projection_refs=projection_refs,
        state_snapshot_id=state_snapshot_id,
        binding_ref={
            "artifact_root_path_hash": artifact_root_hash,
            "binding_status": "verified",
            "database_path_hash": database_hash,
        },
    )


def _active_release_ref(loaded_release: Mapping[str, Any], release: Mapping[str, Any]) -> dict[str, Any]:
    release_id = str(loaded_release.get("release_id") or release.get("release_id") or "")
    release_version = str(loaded_release.get("release_version") or release.get("release_version") or "")
    fingerprint = str(loaded_release.get("fingerprint") or release.get("fingerprint") or release.get("release_fingerprint") or "")
    return {
        "semantic_release_id": release_id,
        "semantic_release_version": release_version,
        "release_id": release_id,
        "release_version": release_version,
        "release_fingerprint": fingerprint,
        "release_path": str(loaded_release.get("release_path") or ""),
        "master_taxonomy_release_id": str(
            loaded_release.get("master_taxonomy_release_id")
            or release.get("master_taxonomy_release_id")
            or ""
        ),
        "runtime_locale": str(loaded_release.get("runtime_locale") or release.get("runtime_locale") or ""),
    }


def _taxonomy_ref(release: Mapping[str, Any], active_release_ref: Mapping[str, Any]) -> dict[str, Any]:
    taxonomy = dict(release.get("taxonomy") or release.get("taxonomy_ref") or {})
    taxonomy_id = str(
        taxonomy.get("taxonomy_id")
        or release.get("taxonomy_id")
        or active_release_ref.get("master_taxonomy_release_id")
        or ""
    )
    taxonomy_version = str(taxonomy.get("taxonomy_version") or release.get("taxonomy_version") or "")
    taxonomy_fingerprint = str(
        taxonomy.get("taxonomy_fingerprint")
        or taxonomy.get("fingerprint")
        or release.get("taxonomy_fingerprint")
        or ""
    )
    return {
        "taxonomy_id": taxonomy_id,
        "taxonomy_version": taxonomy_version,
        "taxonomy_fingerprint": taxonomy_fingerprint,
    }


def _projection_refs(release: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    projections = release.get("projections") or release.get("projection_refs") or ()
    if not isinstance(projections, list):
        return ()
    for projection in projections:
        if not isinstance(projection, Mapping):
            continue
        refs.append(
            {
                "projection_id": str(projection.get("projection_id") or ""),
                "projection_fingerprint": str(
                    projection.get("projection_fingerprint") or projection.get("fingerprint") or ""
                ),
            }
        )
    return tuple(refs)


def _file_fingerprint(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "sha256:" + stable_hash(str(path))
    return "sha256:" + stable_hash(f"{path.resolve(strict=False)}:{stat.st_size}:{stat.st_mtime_ns}")


def _path_fingerprint(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "sha256:" + stable_hash(str(path))
    return "sha256:" + stable_hash(f"{path.resolve(strict=False)}:{stat.st_mtime_ns}")
