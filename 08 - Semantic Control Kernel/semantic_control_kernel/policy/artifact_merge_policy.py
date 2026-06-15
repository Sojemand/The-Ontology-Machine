from __future__ import annotations

from pathlib import PurePosixPath
from typing import Mapping

from semantic_control_kernel.repository.paths import stable_hash


ARTIFACT_NAMESPACE_ROOTS: tuple[str, ...] = (
    "Documents/originals",
    "Documents/raw_extracts",
    "Documents/page_images",
    "Documents/requests",
    "Documents/structured",
    "Documents/validation",
    "Documents/normalized",
    "Documents/logs/imported",
)


def target_artifact_path(
    *,
    source_database_id: str,
    source_relative_path: str,
    source_content_hash: str,
    existing_target_paths: set[str] | None = None,
) -> str:
    relative = _clean_relative(source_relative_path)
    existing = set(existing_target_paths or set())
    root = _namespace_root(relative)
    if relative not in existing:
        return relative
    namespaced = f"{root}/{source_database_id}/{_strip_root(relative, root)}"
    if namespaced not in existing:
        return namespaced
    suffix = stable_hash(f"{source_database_id}:{source_content_hash}:{relative}")[:8]
    path = PurePosixPath(namespaced)
    return str(path.with_name(f"{path.stem}.{suffix}{path.suffix}")).replace("\\", "/")


def artifact_alias_allowed(source_a: Mapping[str, object], source_b: Mapping[str, object]) -> bool:
    return (
        str(source_a.get("source_original_file_name", "")) == str(source_b.get("source_original_file_name", ""))
        and str(source_a.get("source_content_hash", "")) == str(source_b.get("source_content_hash", ""))
    )


def missing_artifact_blocks(record_ref: Mapping[str, object]) -> bool:
    return not bool(record_ref.get("owner_optional_artifact_proof"))


def _namespace_root(relative: str) -> str:
    for root in ARTIFACT_NAMESPACE_ROOTS:
        if relative == root or relative.startswith(f"{root}/"):
            return root
    return "Documents/logs/imported"


def _strip_root(relative: str, root: str) -> str:
    if relative == root:
        return PurePosixPath(relative).name
    return relative[len(root) + 1 :]


def _clean_relative(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Artifact merge paths must be relative and stay inside the Artifact Tree.")
    return str(path)
