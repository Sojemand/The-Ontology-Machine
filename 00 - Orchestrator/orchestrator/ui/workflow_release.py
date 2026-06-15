"""Semantic-release activation workflow for Orchestrator UI actions."""

from __future__ import annotations

from pathlib import Path

from ..pipeline import OrchestratorEngine
from ..pipeline import release_workflow as pipeline_release_workflow
from . import dialogs, repository, validation
from .types import ACTIVATE_RELEASE_WORKER_ACTION


def activate_selected_release(app) -> None:
    if app._processing:
        return
    app._flush_pending_saves()
    app._save_ui_state()
    fields = repository.read_fields(app)
    try:
        validation.ensure_release_activation_ready(fields)
        ui_state = fields.to_ui_state()
        release_path = Path(ui_state.semantic_release_path)
        corpus_db_path = Path(ui_state.selected_corpus_db_path)
        app._append_log(f"[RELEASE-CHECK] Preflight for {release_path.name}")
        preflight = _load_release_preflight(app, ui_state)
        confirmation_payload = _resolve_activation_confirmation(app, ui_state, preflight)
        if confirmation_payload is False:
            app._append_log(f"[RELEASE] Activation cancelled: {release_path.name}")
            return
        worker_payload = {"ui_state": ui_state.to_dict()}
        if isinstance(confirmation_payload, dict):
            worker_payload["activation_confirmation"] = confirmation_payload
        app._append_log(f"[RELEASE] Activation started for {release_path.name} -> {corpus_db_path}")
        app._start_worker(action=ACTIVATE_RELEASE_WORKER_ACTION, ui_state=ui_state, worker_payload=worker_payload)
    except Exception as exc:
        app._append_log(f"[ERROR] Release activation failed: {exc}")
        dialogs.show_error(str(exc))


def _load_release_preflight(app, ui_state):
    engine = OrchestratorEngine(orchestrator_root=app._project_root)
    try:
        return engine.activation_preflight(ui_state)
    except Exception as exc:
        raise ValueError(
            pipeline_release_workflow.build_activation_blocked_message(
                str(exc),
                release_path=Path(ui_state.semantic_release_path),
                corpus_db_path=Path(ui_state.selected_corpus_db_path),
            )
        ) from exc
    finally:
        engine.close()


def _resolve_activation_confirmation(app, ui_state, preflight):
    if bool(preflight.get("no_op")) or not bool(preflight.get("requires_confirmation")):
        return None
    release_path = Path(ui_state.semantic_release_path)
    corpus_db_path = Path(ui_state.selected_corpus_db_path)
    title, body = pipeline_release_workflow.build_activation_confirmation_prompt(
        preflight,
        release_path=release_path,
        corpus_db_path=corpus_db_path,
    )
    if not dialogs.confirm_release_activation(app, title=title, body=body):
        return False
    return pipeline_release_workflow.build_confirmation_payload(
        preflight,
        corpus_db_path=corpus_db_path,
        decision="activate_only",
    )
