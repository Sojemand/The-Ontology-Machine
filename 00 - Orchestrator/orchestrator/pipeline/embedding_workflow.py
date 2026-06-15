"""Embedding stage workflow for automatic runs and manual backfills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import EmbeddingStageResult
from ..models import utc_now_iso
from . import artifact_repository, debug, runtime_retention, storage_repository


_EMBED_STAGE_STATUS = {"completed": "Done", "disabled": "Warning", "skipped": "Skipped"}


def run_embeddings(engine: Any, ui_state: Any) -> EmbeddingStageResult:
    with storage_repository.mutation_lock(engine, "Embeddings"):
        storage_repository.reload_state(engine)
        run_id = f"embeddings-{utc_now_iso().replace(':', '-')}"
        runtime_dir = engine._runtime_root / run_id
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
        previous_log_path = engine._active_log_path
        engine._active_log_path = runtime_dir / "run.log"
        debug.reset_snapshot(engine, total=0)
        debug.append_log(engine, f"Embeddings run {run_id} started")
        try:
            return execute_embedding_stage(engine, storage_repository.corpus_db_path(ui_state))
        finally:
            engine._snapshot.is_running = False
            debug.emit_snapshot(engine)
            artifact_repository.prune_empty_dirs(runtime_dir, stop_at=(engine._state_dir,))
            artifact_repository.prune_empty_dirs(engine._runtime_root, stop_at=(engine._state_dir,))
            debug.append_log(engine, "Embeddings run finished")
            runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
            engine._active_log_path = previous_log_path


def execute_embedding_stage(engine: Any, corpus_db_path: Path) -> EmbeddingStageResult:
    if not corpus_db_path.exists():
        result = EmbeddingStageResult(status="error", count=0, reason="No corpus.db available")
        _finalize_embedding_stage(engine, result)
        return result
    debug.set_stage(engine, "Embeddings", "Processing...", corpus_db_path.name)
    debug.emit_snapshot(engine)
    debug.check_cancelled(engine)
    try:
        result = engine._modules.generate_embeddings(corpus_db_path)
    except Exception as exc:
        result = EmbeddingStageResult(status="error", count=0, reason=str(exc) or "Embedding error")
    _finalize_embedding_stage(engine, result)
    return result


def is_blocking_embedding_result(result: EmbeddingStageResult) -> bool:
    return result.status not in _EMBED_STAGE_STATUS


def _finalize_embedding_stage(engine: Any, result: EmbeddingStageResult) -> None:
    stage_status = _EMBED_STAGE_STATUS.get(result.status, "Error")
    detail = _embedding_detail(result)
    prefix = "[EMBED-WARN]" if stage_status == "Warning" else "[EMBED]" if stage_status != "Error" else "[EMBED-ERROR]"
    debug.set_stage(engine, "Embeddings", stage_status, detail)
    debug.append_log(engine, f"{prefix} {detail}")
    debug.emit_snapshot(engine)


def _embedding_detail(result: EmbeddingStageResult) -> str:
    detail = str(result.reason or "").strip()
    if detail:
        return detail
    if result.status == "completed":
        return f"{result.count} embeddings generated." if result.count else "No new embeddings generated."
    if result.status == "disabled":
        return "Embeddings disabled."
    if result.status == "skipped":
        return "Embeddings skipped."
    return "Embedding error"
