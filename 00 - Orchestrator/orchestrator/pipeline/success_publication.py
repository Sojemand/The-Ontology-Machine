"""Helpers for success artifact publication and cleanup."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

from . import artifact_repository, policy, storage_repository, validation
from .artifact_repository_files import atomic_copy_file


def publish_file(
    engine: Any,
    source: Path,
    target: Path,
    *,
    allowed_roots: tuple[Path, ...],
    action: str,
    noun: str,
) -> str:
    if source == target:
        return ""
    if not validation.ensure_managed_path(engine, source, allowed_roots, action=action, noun=noun):
        return f"{noun} is outside the pipeline: {source}"
    if not source.exists() or not source.is_file():
        return f"{noun} is missing: {source}"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        atomic_copy_file(source, target)
    except Exception as exc:
        return f"{noun} could not be published: {exc}"
    return ""


def cleanup_published_targets(engine: Any, targets: list[Path], allowed_roots: tuple[Path, ...]) -> None:
    for target in reversed(targets):
        artifact_repository.remove_file(engine, target, allowed_roots=allowed_roots)


def cleanup_working_paths(
    engine: Any,
    paths: list[Path],
    allowed_roots: tuple[Path, ...],
    *,
    keep_paths: list[Path],
) -> None:
    keep_resolved = {validation.resolved_path(path) for path in keep_paths}
    for path in paths:
        if validation.resolved_path(path) in keep_resolved:
            continue
        artifact_repository.remove_file(engine, path, allowed_roots=allowed_roots)


def collect_working_paths(record: Any) -> list[Path]:
    seen: set[Path] = set()
    working_paths: list[Path] = []
    for path_text in (
        *record.artifacts.optimizer_raw_paths,
        *record.artifacts.optimizer_page_image_paths,
        *getattr(record.artifacts, "optimizer_ocr_request_paths", []),
        getattr(record.artifacts, "optimizer_ocr_request_path", ""),
        *getattr(record.artifacts, "interpreter_request_paths", []),
        record.artifacts.interpreter_request_path,
        *getattr(record.artifacts, "structured_paths", []),
        record.artifacts.interpreter_debug_bundle_path,
        record.artifacts.structured_path,
        *getattr(record.artifacts, "validation_report_paths", []),
        record.artifacts.validation_report_path,
        *getattr(record.artifacts, "normalized_paths", []),
        record.artifacts.normalized_path,
        *getattr(record.artifacts, "normalizer_request_paths", []),
        getattr(record.artifacts, "normalizer_request_path", ""),
    ):
        if not str(path_text).strip():
            continue
        candidate = Path(path_text)
        if candidate in seen:
            continue
        seen.add(candidate)
        working_paths.append(candidate)
    return working_paths


def existing_path(path_text: str) -> Path:
    return Path(str(path_text).strip())


def raw_target_path(engine: Any, record: Any, source: Path, *, index: int) -> Path:
    if index == 0:
        return policy.raw_output_path(engine, record)
    return policy.raw_output_path(engine, record).with_name(source.name)


def published_original_target(engine: Any, record: Any, route_root: Path) -> Path:
    target = storage_repository.publication_root(route_root, "originals") / policy.record_relative_output_path(
        engine,
        record,
        purpose="Originals archive",
    )
    if not target.exists():
        return target
    if target.is_dir():
        return target
    if artifact_repository.path_matches_hash(target, record.content_hash):
        return target
    matching_conflict = _matching_published_conflict_target(target, record.content_hash)
    if matching_conflict is not None:
        return matching_conflict
    return policy.conflict_target(target, action="archive", content_hash=record.content_hash)


def _matching_published_conflict_target(target: Path, content_hash: str) -> Path | None:
    if not content_hash:
        return None
    for candidate in policy.conflict_target_candidates(target, action="archive", content_hash=content_hash):
        if not candidate.exists():
            return None
        if candidate.is_file() and artifact_repository.path_matches_hash(candidate, content_hash):
            return candidate
    return None
