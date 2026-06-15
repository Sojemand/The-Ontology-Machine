from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..models.serialization import atomic_file_write


MERGEABLE_ARTIFACT_ROOTS = (
    "Documents",
    "Error Cases",
)

CONTROL_LOG_PREFIX = "Documents/logs/merge_runs/"


def artifact_path_mappings(
    selection: Mapping[str, Any],
    id_mappings: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    target_root = Path(str(selection.get("target_artifact_root") or "")).resolve(strict=False)
    mappings: list[dict[str, Any]] = []
    used_target_paths = _existing_artifact_paths(target_root)
    mapped_source_paths: set[str] = set()
    mapped_copy_pairs: set[tuple[str, str]] = set()
    for item in id_mappings or ():
        if not isinstance(item, Mapping):
            continue
        source_root = Path(str(item.get("source_artifact_root") or "")).resolve(strict=False)
        source_artifact_path = str(item.get("source_artifact_path") or "").replace("\\", "/")
        target_artifact_path = str(item.get("target_artifact_path") or "").replace("\\", "/")
        source_path = (source_root / source_artifact_path).resolve(strict=False)
        mapped_source_paths.add(str(source_path))
        copy_key = (str(source_path), target_artifact_path)
        if copy_key in mapped_copy_pairs:
            continue
        mapped_copy_pairs.add(copy_key)
        used_target_paths.add(target_artifact_path)
        mappings.append(
            {
                "mapping_kind": "document_artifact",
                "source_database_id": str(item.get("source_database_id") or ""),
                "source_document_id": str(item.get("source_document_id") or ""),
                "target_document_id": str(item.get("target_document_id") or ""),
                "source_artifact_root": str(source_root),
                "source_artifact_path": source_artifact_path,
                "source_path": str(source_path),
                "target_artifact_root": str(target_root),
                "target_artifact_path": target_artifact_path,
                "target_path": str(target_root / target_artifact_path),
                "copy_status": "planned",
            }
        )
    mappings.extend(_tree_file_mappings(selection, target_root, used_target_paths, mapped_source_paths))
    return mappings


def copy_artifact_mappings(artifact_mappings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    copied: list[dict[str, Any]] = []
    for mapping in artifact_mappings:
        source_path = Path(str(mapping.get("source_path") or "")).resolve(strict=False)
        target_root = Path(str(mapping.get("target_artifact_root") or "")).resolve(strict=False)
        target_artifact_path = str(mapping.get("target_artifact_path") or "").replace("\\", "/")
        target_path = (target_root / target_artifact_path).resolve(strict=False)
        _validate_copy_paths(source_path, target_root, target_path, target_artifact_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve(strict=False) != target_path.resolve(strict=False):
            atomic_file_write(target_path, lambda tmp_path, source=source_path: shutil.copy2(source, tmp_path))
        copied.append(
            {
                **dict(mapping),
                "copy_status": "copied",
                "target_size_bytes": target_path.stat().st_size,
                "target_sha256": _sha256(target_path),
            }
        )
    return {
        "copied_artifact_count": len(copied),
        "copied_artifact_mappings": copied,
    }


def stage_artifact_mappings(artifact_mappings: Sequence[Mapping[str, Any]], staging_root: str | Path) -> dict[str, Any]:
    root = Path(staging_root).resolve(strict=False)
    staged: list[dict[str, Any]] = []
    for mapping in artifact_mappings:
        source_path = Path(str(mapping.get("source_path") or "")).resolve(strict=False)
        target_root = Path(str(mapping.get("target_artifact_root") or "")).resolve(strict=False)
        target_artifact_path = str(mapping.get("target_artifact_path") or "").replace("\\", "/")
        target_path = (target_root / target_artifact_path).resolve(strict=False)
        _validate_copy_paths(source_path, target_root, target_path, target_artifact_path)
        if source_path.resolve(strict=False) == target_path.resolve(strict=False):
            stage_path = target_path
            stage_status = "already_present"
        else:
            stage_path = (root / target_artifact_path).resolve(strict=False)
            _validate_stage_path(root, stage_path)
            stage_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_file_write(stage_path, lambda tmp_path, source=source_path: shutil.copy2(source, tmp_path))
            stage_status = "staged"
        staged.append(
            {
                **dict(mapping),
                "copy_status": "staged",
                "stage_status": stage_status,
                "stage_path": str(stage_path),
                "stage_size_bytes": stage_path.stat().st_size,
                "stage_sha256": _sha256(stage_path),
            }
        )
    return {
        "staging_root": str(root),
        "staged_artifact_count": len(staged),
        "staged_artifact_mappings": staged,
    }


def promote_staged_artifact_mappings(staged_artifact_mappings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    copied: list[dict[str, Any]] = []
    for mapping in staged_artifact_mappings:
        stage_path = Path(str(mapping.get("stage_path") or "")).resolve(strict=False)
        target_root = Path(str(mapping.get("target_artifact_root") or "")).resolve(strict=False)
        target_artifact_path = str(mapping.get("target_artifact_path") or "").replace("\\", "/")
        target_path = (target_root / target_artifact_path).resolve(strict=False)
        _validate_copy_paths(stage_path, target_root, target_path, target_artifact_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if stage_path.resolve(strict=False) != target_path.resolve(strict=False):
            atomic_file_write(target_path, lambda tmp_path, source=stage_path: shutil.copy2(source, tmp_path))
        copied.append(
            {
                **dict(mapping),
                "copy_status": "copied",
                "target_size_bytes": target_path.stat().st_size,
                "target_sha256": _sha256(target_path),
            }
        )
    return {
        "copied_artifact_count": len(copied),
        "copied_artifact_mappings": copied,
    }


def cleanup_staged_artifacts(staging_root: str | Path) -> dict[str, Any]:
    root = Path(staging_root).resolve(strict=False)
    if root.name != "artifact_staging":
        raise ValueError(f"Refusing to clean unexpected artifact staging root: {root}")
    if not root.exists():
        return {"staging_root": str(root), "cleanup_status": "not_found"}
    try:
        shutil.rmtree(root)
    except OSError as exc:
        return {"staging_root": str(root), "cleanup_status": "cleanup_pending", "error": str(exc)}
    return {"staging_root": str(root), "cleanup_status": "removed"}


def _validate_copy_paths(source_path: Path, target_root: Path, target_path: Path, target_artifact_path: str) -> None:
    if not source_path.exists():
        raise ValueError(f"source_artifact_missing: source artifact does not exist: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"source_artifact_missing: source artifact is not a file: {source_path}")
    try:
        target_path.relative_to(target_root)
    except ValueError as exc:
        raise ValueError("artifact ref escapes the active target artifact root.") from exc
    if not target_artifact_path or target_artifact_path.startswith("../") or "/../" in target_artifact_path:
        raise ValueError("artifact ref escapes the active target artifact root.")


def _validate_stage_path(staging_root: Path, stage_path: Path) -> None:
    try:
        stage_path.relative_to(staging_root)
    except ValueError as exc:
        raise ValueError("artifact staging path escapes the merge staging root.") from exc


def _tree_file_mappings(
    selection: Mapping[str, Any],
    target_root: Path,
    used_target_paths: set[str],
    mapped_source_paths: set[str],
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for source in selection.get("source_databases", []):
        if not isinstance(source, Mapping):
            continue
        if str(source.get("source_state") or "") == "empty":
            continue
        source_database_id = str(source.get("source_database_id") or "")
        source_root = Path(str(source.get("source_artifact_root") or "")).resolve(strict=False)
        for source_path, source_artifact_path in _iter_mergeable_tree_files(source_root):
            resolved_source = str(source_path.resolve(strict=False))
            if resolved_source in mapped_source_paths:
                continue
            target_artifact_path = _target_tree_artifact_path(
                source_database_id=source_database_id,
                source_artifact_path=source_artifact_path,
                source_hash=_sha256(source_path),
                used_target_paths=used_target_paths,
            )
            mapped_source_paths.add(resolved_source)
            used_target_paths.add(target_artifact_path)
            mappings.append(
                {
                    "mapping_kind": "tree_artifact",
                    "source_database_id": source_database_id,
                    "source_document_id": "",
                    "target_document_id": "",
                    "source_artifact_root": str(source_root),
                    "source_artifact_path": source_artifact_path,
                    "source_path": resolved_source,
                    "target_artifact_root": str(target_root),
                    "target_artifact_path": target_artifact_path,
                    "target_path": str(target_root / target_artifact_path),
                    "copy_status": "planned",
                }
            )
    return mappings


def _iter_mergeable_tree_files(source_root: Path) -> list[tuple[Path, str]]:
    if not source_root.exists():
        return []
    files: list[tuple[Path, str]] = []
    for root_name in MERGEABLE_ARTIFACT_ROOTS:
        root = source_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                files.append((path, path.relative_to(source_root).as_posix()))
    return sorted(files, key=lambda item: item[1])


def _target_tree_artifact_path(
    *,
    source_database_id: str,
    source_artifact_path: str,
    source_hash: str,
    used_target_paths: set[str],
) -> str:
    relative = source_artifact_path.replace("\\", "/")
    if relative.startswith(CONTROL_LOG_PREFIX):
        relative = f"Documents/logs/imported/{source_database_id}/{relative[len('Documents/logs/'):]}"
    if relative not in used_target_paths:
        return relative
    path = Path(relative)
    namespaced = Path(path.parent) / source_database_id / path.name
    namespaced_posix = namespaced.as_posix()
    if namespaced_posix not in used_target_paths:
        return namespaced_posix
    suffix = source_hash.split(":", 1)[-1][:8]
    return (namespaced.parent / f"{path.stem}.{suffix}{path.suffix}").as_posix()


def _existing_artifact_paths(target_root: Path) -> set[str]:
    if not target_root.exists():
        return set()
    return {
        path.relative_to(target_root).as_posix()
        for path in target_root.rglob("*")
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
