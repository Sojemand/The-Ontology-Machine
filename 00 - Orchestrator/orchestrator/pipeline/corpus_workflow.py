"""Corpus Builder stage workflow for successful records."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..integrations import stage_name_for_module
from . import debug, embedding_workflow, error_workflow
from .page_stage_types import PageStageResult


def load_page_into_corpus(
    engine: Any,
    record: Any,
    ctx: Any,
    paths: Any,
    raw_path: Path,
    structured_path: Path,
    validation_path: Path,
    normalized_path: Path,
    *,
    page_index: int,
    page_total: int,
) -> PageStageResult:
    stage_name = stage_name_for_module("corpus_builder")
    debug.check_cancelled(engine)
    debug.set_stage(
        engine,
        stage_name,
        "Processing...",
        _page_detail(normalized_path, page_index, page_total),
        progress_current=page_index,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    page_images_dir = _common_page_images_dir(record)
    corpus_result = engine._modules.load_document(
        structured_path,
        validation_path,
        normalized_path,
        raw_path,
        paths.corpus_db_path,
        persist_page_images_in_db=page_images_dir is not None,
        page_images_dir=page_images_dir,
    )
    if corpus_result.status not in {"loaded", "archived_and_loaded", "skipped"}:
        return PageStageResult.failure(corpus_result.reason or corpus_result.status or "Corpus error")
    debug.set_stage(
        engine,
        stage_name,
        corpus_result.status,
        corpus_result.reason,
        progress_current=page_index + 1,
        progress_total=page_total,
        progress_label="Pages",
    )
    debug.emit_snapshot(engine)
    return PageStageResult.success(status=corpus_result.status)


def finalize_loaded_pages(engine: Any, record: Any, ctx: Any, paths: Any) -> bool:
    embedding_result = embedding_workflow.execute_embedding_stage(engine, paths.corpus_db_path)
    if embedding_workflow.is_blocking_embedding_result(embedding_result):
        error_workflow.handle_failure(
            engine,
            record,
            ctx,
            "Embeddings",
            embedding_result.reason or "Embedding error",
        )
        return False
    return error_workflow.finalize_success(engine, record, ctx, paths)


def _common_page_images_dir(record: Any) -> Path | None:
    paths = [
        Path(str(path_text).strip())
        for path_text in getattr(record.artifacts, "optimizer_page_image_paths", []) or []
        if str(path_text).strip()
    ]
    if not paths:
        return None
    parents = [path.parent for path in paths]
    if not parents:
        return None
    resolved_parents = [path.expanduser().resolve(strict=False) for path in parents]
    first_parent = resolved_parents[0]
    if all(parent == first_parent for parent in resolved_parents):
        return parents[0]
    try:
        return Path(os.path.commonpath([str(parent) for parent in resolved_parents]))
    except ValueError:
        return None


def _page_detail(path: Path, page_index: int, page_total: int) -> str:
    if page_total <= 1:
        return path.name
    return f"Page {page_index + 1}/{page_total} | {path.name}"
