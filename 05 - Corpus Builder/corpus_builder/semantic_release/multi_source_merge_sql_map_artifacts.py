from __future__ import annotations

import re
import sqlite3
from pathlib import Path, PurePosixPath

from .multi_source_merge_types import stable_hash

ARTIFACT_NAMESPACE_ROOTS = (
    "Documents/originals",
    "Documents/raw_extracts",
    "Documents/page_images",
    "Documents/requests",
    "Documents/structured",
    "Documents/validation",
    "Documents/normalized",
    "Documents/logs/imported",
)


def source_artifact_path(row: sqlite3.Row, source_artifact_root: Path) -> str:
    file_path = str(row["file_path"] or "")
    original_relative = original_artifact_path(row, file_path)
    if not file_path:
        return original_relative
    tree_relative = tree_relative_path(file_path, source_artifact_root)
    if tree_relative:
        return tree_relative
    if (source_artifact_root / original_relative).is_file():
        return original_relative
    return original_relative


def existing_artifact_paths(target_root: Path) -> set[str]:
    if not target_root.exists():
        return set()
    return {
        path.relative_to(target_root).as_posix()
        for path in target_root.rglob("*")
        if path.is_file()
    }


def target_artifact_path(
    *,
    source_database_id: str,
    source_relative_path: str,
    source_content_hash: str,
    existing_target_paths: set[str],
) -> str:
    relative = clean_relative(source_relative_path)
    root = namespace_root(relative)
    if relative not in existing_target_paths:
        return relative
    namespaced = f"{root}/{source_database_id}/{strip_root(relative, root)}"
    if namespaced not in existing_target_paths:
        return namespaced
    suffix = stable_hash(f"{source_database_id}:{source_content_hash}:{relative}")[:8]
    path = PurePosixPath(namespaced)
    return str(path.with_name(f"{path.stem}.{suffix}{path.suffix}"))


def original_artifact_path(row: sqlite3.Row, file_path: str) -> str:
    file_name = str(row["file_name"] or Path(file_path).name or "source")
    return f"Documents/originals/{Path(file_name).name}"


def tree_relative_path(file_path: str, source_artifact_root: Path) -> str:
    candidate = Path(file_path)
    if candidate.is_absolute() or looks_windows_absolute(file_path):
        try:
            return clean_relative(candidate.resolve(strict=False).relative_to(source_artifact_root).as_posix())
        except ValueError:
            return ""
    if looks_external_or_escaping(file_path):
        return ""
    try:
        return clean_relative(file_path)
    except ValueError:
        return ""


def namespace_root(relative: str) -> str:
    for root in ARTIFACT_NAMESPACE_ROOTS:
        if relative == root or relative.startswith(f"{root}/"):
            return root
    return "Documents/logs/imported"


def strip_root(relative: str, root: str) -> str:
    if relative == root:
        return PurePosixPath(relative).name
    return relative[len(root) + 1 :]


def clean_relative(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Artifact merge paths must be relative and stay inside the Artifact Tree.")
    return str(path)


def looks_external_or_escaping(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    path = PurePosixPath(normalized)
    return looks_windows_absolute(normalized) or normalized.startswith("/") or ".." in path.parts


def looks_windows_absolute(file_path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:/", file_path.replace("\\", "/")))
