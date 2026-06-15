"""Debug run batch execution helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ..context import ModuleContext
from ..models import LoadBatchResult
from ..semantic_release import load_active_release, validate_payload_against_release
from ..services import load_module_config
from . import debug_common_workflow, debug_preview, debug_support


def preview_for_run(context: ModuleContext, command) -> dict:
    corpus_db_path = command.output_root / "corpus.db"
    if command.mode == "single":
        return debug_preview.build_single_preview(
            context,
            source_path=command.source_path,
            corpus_db_path=corpus_db_path,
        )
    return debug_preview.build_scan_preview(context, input_root=command.input_root, corpus_db_path=corpus_db_path)


def run_batches(
    context: ModuleContext,
    command,
    *,
    bundles: list,
    base_metrics: dict[str, int],
    load_batch_fn,
) -> tuple[LoadBatchResult, bool, dict]:
    if command.mode != "batch":
        replace_existing_db_files(command.output_root / "corpus.db")
        batch = load_batch_fn(context, bundles, persist_page_images_in_db=command.persist_page_images_in_db)
        append_bundle_logs(command.session_root, bundles, batch)
        return batch, False, {}
    config = load_module_config(context)
    release, active_release_path = load_active_release(context, config)
    validate_bundles_against_release(bundles, release)
    corpus_db_path = command.output_root / "corpus.db"
    replaced_existing = replace_existing_db_files(corpus_db_path)
    batch = LoadBatchResult()
    total = len(bundles)
    for index, bundle in enumerate(bundles, 1):
        if debug_support.cancel_requested(command.session_root):
            return batch, True, debug_common_workflow.release_meta(release, active_release_path, replaced_existing)
        part = load_batch_fn(context, [bundle], persist_page_images_in_db=command.persist_page_images_in_db)
        merge_batch(batch, part)
        append_bundle_logs(command.session_root, [bundle], part)
        debug_support.write_snapshot(
            command.session_root,
            status="running",
            detail=f"{index}/{total} Artefakte verarbeitet",
            processed=index,
            total=total,
            counters={**base_metrics, "loaded": batch.loaded, "skipped": batch.skipped, "archived": batch.archived, "errors": batch.errors},
        )
    return batch, debug_support.cancel_requested(command.session_root), debug_common_workflow.release_meta(release, active_release_path, replaced_existing)


def validate_bundles_against_release(bundles: list, release: dict) -> None:
    incompatible: list[str] = []
    for bundle in bundles:
        payload = json.loads(bundle.normalized_path.read_text(encoding="utf-8"))
        try:
            validate_payload_against_release(payload, release)
        except ValueError as exc:
            incompatible.append(f"{bundle.normalized_path.name}: {exc}")
    if incompatible:
        raise ValueError(f"Rebuild abgebrochen: {' | '.join(incompatible[:5])}")


def replace_existing_db_files(db_path: Path) -> bool:
    replaced = False
    for path in (db_path, db_path.with_name(f"{db_path.name}-shm"), db_path.with_name(f"{db_path.name}-wal")):
        if path.exists():
            path.unlink()
            replaced = True
    return replaced


def append_bundle_logs(session_root: Path, bundles: list, batch: LoadBatchResult) -> None:
    for bundle, item in zip(bundles, batch.results):
        suffix = f" ({item.reason})" if item.reason else ""
        debug_support.append_log(session_root, f"[ITEM] {bundle.normalized_path.name}: {item.status}{suffix}")


def merge_batch(target: LoadBatchResult, source: LoadBatchResult) -> None:
    target.loaded += source.loaded
    target.skipped += source.skipped
    target.archived += source.archived
    target.errors += source.errors
    target.results.extend(source.results)
