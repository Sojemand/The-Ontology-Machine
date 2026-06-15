"""Artifact promotion, cleanup and archive operations for the pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import page_image_assets, policy, storage_repository, validation
from .artifact_repository_files import (
    atomic_copy_file,
    copy_if_exists,
    move_file_with_conflict_handling,
    path_matches_hash,
    prune_empty_dirs,
    remove_file,
)


def promote_pipeline_output(
    engine: Any,
    source_path: Path,
    target_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    missing_message: str,
    outside_message: str,
    copy_message: str,
    action: str,
    noun: str,
) -> str:
    if not str(source_path).strip():
        return missing_message
    if not validation.ensure_managed_path(engine, source_path, allowed_roots, action=action, noun=noun):
        return outside_message
    if not source_path.exists() or not source_path.is_file():
        return f"{copy_message}: {source_path}"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and target_path.is_dir():
        if not validation.ensure_managed_path(engine, target_path, allowed_roots, action=action, noun=f"{noun} target"):
            return f"{copy_message}: invalid target."
        shutil.rmtree(target_path, ignore_errors=True)
    try:
        if source_path != target_path:
            atomic_copy_file(source_path, target_path)
        elif not target_path.exists():
            return f"{copy_message}: {target_path}"
    except Exception as exc:
        return f"{copy_message}: {exc}"
    if source_path != target_path and validation.is_within(validation.resolved_path(source_path), validation.resolved_path(engine._state_dir)):
        remove_file(engine, source_path, allowed_roots=allowed_roots)
    return ""


def promote_structured_output(engine: Any, source_path: Path, target_path: Path, *, allowed_roots: tuple[Path, ...]) -> str:
    return promote_pipeline_output(
        engine,
        source_path,
        target_path,
        allowed_roots=allowed_roots,
        missing_message="Interpreter did not provide structured output.",
        outside_message="Structured output could not be imported: interpreter output is outside the pipeline.",
        copy_message="Structured output could not be imported",
        action="Structured-Output",
        noun="Interpreter-Output",
    )


def cleanup_normal_outputs(engine: Any, record: Any, *, allowed_roots: tuple[Path, ...]) -> None:
    extra_render_paths = page_image_assets.extra_render_paths_from_raws(
        record.artifacts.optimizer_raw_paths,
        known_path_values=record.artifacts.optimizer_page_image_paths,
    )
    for path_str in record.artifacts.optimizer_raw_paths:
        remove_file(engine, Path(path_str), allowed_roots=allowed_roots)
    for path_str in record.artifacts.optimizer_page_image_paths:
        remove_file(engine, Path(path_str), allowed_roots=allowed_roots)
    for path in extra_render_paths:
        remove_file(engine, path, allowed_roots=allowed_roots)
    cleanup_temp_outputs(engine, record, allowed_roots=allowed_roots)
    record.artifacts.clear_normal_outputs()


def cleanup_temp_outputs(engine: Any, record: Any, *, allowed_roots: tuple[Path, ...]) -> None:
    list_attrs = (
        "optimizer_ocr_request_paths",
        "interpreter_request_paths",
        "structured_paths",
        "normalized_paths",
        "normalizer_request_paths",
        "validation_report_paths",
    )
    for attr in list_attrs:
        for path_str in getattr(record.artifacts, attr, []):
            if path_str:
                remove_file(engine, Path(path_str), allowed_roots=allowed_roots)
        setattr(record.artifacts, attr, [])
    for attr in (
        "optimizer_ocr_request_path",
        "interpreter_request_path",
        "interpreter_debug_bundle_path",
        "structured_path",
        "normalized_path",
        "normalizer_request_path",
        "validation_report_path",
    ):
        path_str = getattr(record.artifacts, attr)
        if path_str:
            remove_file(engine, Path(path_str), allowed_roots=allowed_roots)
            setattr(record.artifacts, attr, "")


def move_to_originals_archive(engine: Any, record: Any, ctx: Any) -> None:
    source = Path(record.source_path or record.original_source_path)
    if not source.exists():
        return
    if not validation.ensure_managed_path(engine, source, ctx.managed_roots, action="Originals archive", noun="source path"):
        return
    originals_root = storage_repository.publication_root(
        storage_repository.route_artifact_root(ctx.ui_state, record.route_family),
        "originals",
    )
    destination = originals_root / policy.record_relative_output_path(engine, record, purpose="Originals-Archiv")
    archived_target = move_file_with_conflict_handling(
        engine, source, destination, action="archive", content_hash=record.content_hash, allowed_roots=ctx.managed_roots
    )
    if archived_target is not None:
        record.source_path = str(archived_target)
        record.current_location = "originals_archive"


def remove_file(engine: Any, path: Path, *, allowed_roots: tuple[Path, ...] | None = None) -> None:
    if allowed_roots is not None and not validation.ensure_managed_path(engine, path, allowed_roots, action="File cleanup", noun="file path"):
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return
    prune_empty_dirs(path.parent, stop_at=allowed_roots or ())


def discard_normalized_output(engine: Any, record: Any, *, allowed_roots: tuple[Path, ...]) -> None:
    if record.artifacts.normalized_path:
        remove_file(engine, Path(record.artifacts.normalized_path), allowed_roots=allowed_roots)
        record.artifacts.normalized_path = ""
