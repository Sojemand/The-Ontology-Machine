"""Workflow helpers for worker-process action dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import UiState
from .actions import ACTIVATE_RELEASE_ACTION, CREATE_DATABASE_ACTION, EMBEDDINGS_ACTION, RESET_ACTION, RESET_PIPELINE_LOGS_ACTION, RUN_ACTION


def run_worker_process(
    project_root: str,
    action: str,
    worker_payload: dict,
    event_queue,
    cancel_event,
    *,
    engine_cls,
    cancelled_error,
    busy_error,
) -> None:
    engine = engine_cls(
        orchestrator_root=Path(project_root),
        snapshot_callback=lambda snapshot: event_queue.put(("snapshot", snapshot)),
        log_callback=lambda line: event_queue.put(("log", line)),
        cancel_requested=cancel_event.is_set if cancel_event is not None else None,
    )
    try:
        _dispatch_action(engine, action, worker_payload)
    except cancelled_error:
        event_queue.put(("cancelled", None))
    except busy_error as exc:
        event_queue.put(("error", str(exc)))
    except Exception as exc:
        event_queue.put(("error", str(exc)))
    else:
        event_queue.put(("done", None))
    finally:
        engine.close()


def _dispatch_action(engine, action: str, ui_state: UiState) -> None:
    state = _ui_state_from_payload(ui_state)
    if action == RUN_ACTION:
        engine.run(state)
        return
    if action == RESET_ACTION:
        engine.reset_run_history(state)
        return
    if action == RESET_PIPELINE_LOGS_ACTION:
        engine.reset_pipeline_logs(state)
        return
    if action == EMBEDDINGS_ACTION:
        engine.run_embeddings(state)
        return
    if action == ACTIVATE_RELEASE_ACTION:
        engine.activate_release(
            state,
            confirmation_payload=_activation_confirmation_from_payload(ui_state),
        )
        return
    if action == CREATE_DATABASE_ACTION:
        engine.create_database(
            state,
            request=_create_database_from_payload(ui_state),
        )
        return
    raise ValueError(f"Unknown action: {action}")


def _ui_state_from_payload(payload: Any) -> UiState:
    if isinstance(payload, dict) and "ui_state" in payload:
        value = payload.get("ui_state", {})
        if not isinstance(value, dict):
            raise ValueError("ui_state must be a JSON object.")
        return UiState.from_dict(value)
    if not isinstance(payload, dict):
        raise ValueError("worker_payload must be a JSON object.")
    return UiState.from_dict(payload)


def _activation_confirmation_from_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("activation_confirmation")
    return value if isinstance(value, dict) else None


def _create_database_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("worker_payload must be a JSON object.")
    value = payload.get("create_database")
    if not isinstance(value, dict):
        raise ValueError("create_database must be a JSON object.")
    return value
