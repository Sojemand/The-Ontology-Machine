from __future__ import annotations

from pathlib import Path
from typing import Any

from ..integrations import ReleaseActivationStageResult, stage_name_for_module
from ..integrations.release_activation import activation_preflight as load_activation_preflight
from ..models import utc_now_iso
from . import artifact_repository, debug, runtime_retention, storage_repository
from .release_activation_confirmation import write_confirmation_artifact
from .release_activation_messages import (
    activation_success_detail,
    annotated_release_failure,
    build_activation_blocked_message,
    build_selected_release_needs_activation_message,
)
from .release_activation_utils import selected_release_path


def activation_preflight(engine: Any, ui_state: Any) -> dict[str, Any]:
    release_path = selected_release_path(ui_state)
    if release_path is None:
        raise ValueError("Semantic Release is not set.")
    return load_activation_preflight(
        engine._modules,
        release_path=release_path,
        corpus_db_path=storage_repository.corpus_db_path(ui_state),
    )


def ensure_selected_release_is_active(engine: Any, ui_state: Any) -> None:
    release_path = selected_release_path(ui_state)
    if release_path is None:
        return
    corpus_db_path = storage_repository.corpus_db_path(ui_state)
    stage_name = stage_name_for_module("corpus_builder")
    try:
        preflight = activation_preflight(engine, ui_state)
    except Exception as exc:
        detail = build_activation_blocked_message(str(exc), release_path=release_path, corpus_db_path=corpus_db_path)
        debug.set_stage(engine, stage_name, "Error", detail)
        debug.append_log(engine, f"[RELEASE-ERROR] {detail}")
        debug.emit_snapshot(engine)
        raise RuntimeError(detail) from exc
    if bool(preflight.get("no_op")):
        debug.append_log(engine, f"[RELEASE] Selected release already active: {release_path.name}")
        return
    detail = build_selected_release_needs_activation_message(
        preflight,
        release_path=release_path,
        corpus_db_path=corpus_db_path,
    )
    debug.set_stage(engine, stage_name, "Error", detail)
    debug.append_log(engine, f"[RELEASE-ERROR] {detail}")
    debug.emit_snapshot(engine)
    raise RuntimeError(detail)


def run_release_activation(
    engine: Any,
    ui_state: Any,
    *,
    confirmation_payload: dict[str, Any] | None = None,
) -> ReleaseActivationStageResult:
    with storage_repository.mutation_lock(engine, "Release Activation"):
        storage_repository.reload_state(engine)
        run_id = f"release-activation-{utc_now_iso().replace(':', '-')}"
        runtime_dir = engine._runtime_root / run_id
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
        previous_log_path = engine._active_log_path
        engine._active_log_path = runtime_dir / "run.log"
        debug.reset_snapshot(engine, total=0)
        debug.append_log(engine, f"Release activation {run_id} started")
        try:
            return execute_release_activation(
                engine,
                ui_state,
                runtime_dir=runtime_dir,
                confirmation_payload=confirmation_payload,
            )
        finally:
            _finish_release_activation(engine, previous_log_path, runtime_dir)


def execute_release_activation(
    engine: Any,
    ui_state: Any,
    *,
    runtime_dir: Path,
    confirmation_payload: dict[str, Any] | None = None,
) -> ReleaseActivationStageResult:
    release_path = selected_release_path(ui_state)
    if release_path is None:
        raise ValueError("Semantic Release is not set.")
    corpus_db_path = storage_repository.corpus_db_path(ui_state)
    stage_name = stage_name_for_module("corpus_builder")
    debug.set_stage(engine, stage_name, "Processing...", release_path.name)
    debug.emit_snapshot(engine)
    debug.check_cancelled(engine)
    confirmation_artifact_path = (
        write_confirmation_artifact(runtime_dir, confirmation_payload) if confirmation_payload is not None else None
    )
    try:
        result = engine._modules.activate_semantic_release(
            release_path,
            corpus_db_path,
            confirmation_artifact_path=confirmation_artifact_path,
        )
    except Exception as exc:
        result = ReleaseActivationStageResult(status="error", reason=str(exc))
    if result.status != "applied":
        detail = annotated_release_failure(
            result.reason or "Semantic Release could not be activated.",
            release_path=release_path,
            corpus_db_path=corpus_db_path,
        )
        debug.set_stage(engine, stage_name, "Error", detail)
        debug.append_log(engine, f"[RELEASE-ERROR] {detail}")
        debug.emit_snapshot(engine)
        raise RuntimeError(detail)
    detail = activation_success_detail(result=result, release_path=release_path)
    debug.set_stage(engine, stage_name, "Done", detail)
    debug.append_log(engine, f"[RELEASE] {detail}")
    debug.emit_snapshot(engine)
    return result


def _finish_release_activation(engine: Any, previous_log_path: Path, runtime_dir: Path) -> None:
    engine._snapshot.is_running = False
    debug.emit_snapshot(engine)
    artifact_repository.prune_empty_dirs(runtime_dir, stop_at=(engine._state_dir,))
    artifact_repository.prune_empty_dirs(engine._runtime_root, stop_at=(engine._state_dir,))
    debug.append_log(engine, "Release activation finished")
    runtime_retention.prune_run_history(engine._runtime_root, protected_names={runtime_dir.name})
    engine._active_log_path = previous_log_path
