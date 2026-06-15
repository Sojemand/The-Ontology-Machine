from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .cleanup_database import remove_database_records


def mutate_cleanup_scope(
    *,
    database_path: Path,
    artifact_root: Path,
    record_refs: Sequence[Mapping[str, Any]],
    artifact_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    removable_artifacts = _validated_artifacts(artifact_root, artifact_refs)
    database_report = remove_database_records(database_path, record_refs)
    removed_artifacts = _remove_artifacts(removable_artifacts)
    return {
        **database_report,
        "removed_artifact_refs": removed_artifacts,
        "removed_artifact_count": len(removed_artifacts),
    }


def _validated_artifacts(
    artifact_root: Path,
    artifact_refs: Sequence[Mapping[str, Any]],
) -> list[tuple[Path, dict[str, Any]]]:
    removable: list[tuple[Path, dict[str, Any]]] = []
    for ref in artifact_refs:
        artifact_path = str(ref.get("artifact_path") or "").replace("\\", "/")
        if not artifact_path:
            raise ValueError("records_not_isolated: cleanup artifact refs must include artifact_path.")
        path = (artifact_root / artifact_path).resolve(strict=False)
        try:
            path.relative_to(artifact_root)
        except ValueError as exc:
            raise ValueError("records_not_isolated: cleanup artifact ref escapes the active artifact tree.") from exc
        if not path.exists():
            raise ValueError(f"partial_pipeline_run: cleanup artifact is missing: {artifact_path}")
        if not path.is_file():
            raise ValueError(f"partial_pipeline_run: cleanup artifact ref is not a file: {artifact_path}")
        removable.append((path, {**dict(ref), "artifact_path": artifact_path}))
    return removable


def _remove_artifacts(removable_artifacts: Sequence[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    removed: list[dict[str, Any]] = []
    for path, ref in removable_artifacts:
        path.unlink()
        removed_ref = dict(ref)
        removed_ref["removed"] = True
        removed.append(removed_ref)
    return removed
