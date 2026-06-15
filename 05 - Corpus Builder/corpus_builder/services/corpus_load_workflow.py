"""Batch load service workflow."""

from __future__ import annotations

from pathlib import Path

from ..context import ModuleContext
from ..database import connect, ensure_schema
from ..loader import load_from_file
from ..models.results import LoadBatchResult
from ..models.types import LoadBundle
from ..semantic_release import ensure_mutation_runtime_release
from .config import load_module_config


def load_batch(
    context: ModuleContext,
    bundles: list[LoadBundle],
    *,
    persist_page_images_in_db: bool | None = None,
    page_images_dir: str | Path | None = None,
) -> LoadBatchResult:
    result = LoadBatchResult()
    if not bundles:
        return result

    config = load_module_config(context)
    persist_page_images = config.source.persist_page_images_in_db if persist_page_images_in_db is None else bool(persist_page_images_in_db)
    page_images_root = page_images_dir if page_images_dir is not None else config.source.page_images_dir or None
    releases_by_db: dict[str, dict[str, object]] = {}
    connections = {}
    try:
        for bundle in bundles:
            db_path = str(context.resolve_path(bundle.corpus_db_path))
            conn = connections.get(db_path) or _open_load_connection(context, config, db_path, releases_by_db)
            connections[db_path] = conn
            item = load_from_file(
                conn,
                bundle.normalized_path,
                bundle.validation_path,
                structured_path=bundle.structured_path,
                raw_path=bundle.raw_path,
                semantic_release=releases_by_db[db_path],
                persist_page_images_in_db=persist_page_images,
                page_images_dir=page_images_root,
                persist_original_artifact_in_db=bool(config.source.persist_original_artifact_in_db),
                max_original_artifact_bytes=config.source.max_original_artifact_bytes,
                max_page_image_bytes=config.source.max_page_image_bytes,
                max_page_image_total_bytes=config.source.max_page_image_total_bytes,
            )
            _count_load_result(result, item.status)
            result.results.append(item)
    finally:
        for conn in connections.values():
            conn.close()
    return result


def _open_load_connection(
    context: ModuleContext,
    config,
    db_path: str,
    releases_by_db: dict[str, dict[str, object]],
):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    ensure_schema(conn)
    release, _active_snapshot, seeded = ensure_mutation_runtime_release(conn, context, config)
    if seeded:
        conn.commit()
    releases_by_db[db_path] = release
    return conn


def _count_load_result(result: LoadBatchResult, status: str) -> None:
    if status == "loaded":
        result.loaded += 1
    elif status == "archived_and_loaded":
        result.loaded += 1
        result.archived += 1
    elif status == "skipped":
        result.skipped += 1
    elif status == "error":
        result.errors += 1
