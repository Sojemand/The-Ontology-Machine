"""Path-stable facade for owner-action execution helpers."""
from __future__ import annotations

from types import SimpleNamespace
from tkinter import filedialog as fd

from ..contract_runtime import invoke_module_contract
from . import action_forms, background_jobs, operation_merge, operation_paths, operation_progress, operation_results, operation_routing, operation_state
from .corpus_db_dialog import prompt_new_corpus_db_creation


def run_surface_action(app, surface_id: str, action_link: dict) -> None:
    entry = app._selected_entry()
    if entry is None:
        return
    if action_link.get("requires_saved_surface") and operation_state.has_dirty_drafts(app, entry.slot_name):
        operation_state.remember_result(app, surface_id, action_link, {"status": "error", "reason": "Unsaved changes are present. Please save first."})
        return operation_state.rerender(app)
    try:
        payload = _action_payload(app, surface_id, action_link)
    except Exception as exc:
        operation_state.remember_result(app, surface_id, action_link, {"status": "error", "reason": str(exc)})
        return operation_state.rerender(app)
    if payload is None:
        return
    if surface_id in operation_state.action_loading(app):
        return
    runtime = _runtime()
    if _is_merge_action(action_link):
        return operation_merge.start_merge_flow(app, surface_id, action_link, payload, runtime=runtime)
    try:
        target_root, contract_module, target_payload = operation_routing.action_target(app, entry, action_link, payload)
    except Exception as exc:
        operation_state.remember_result(app, surface_id, action_link, {"status": "error", "reason": str(exc)})
        return operation_state.rerender(app)
    _start_owner_action(app, surface_id, action_link, target_root, contract_module, target_payload, runtime=runtime)


def resolve_merge_interaction(app, surface_id: str, choice_id: str) -> None:
    operation_merge.resolve_merge_interaction(app, surface_id, choice_id, runtime=_runtime())


def result_text(app, surface_id: str) -> str:
    return operation_results.result_text(app, surface_id)


def choose_output_path(app, surface_id: str, action_link: dict):
    return operation_paths.choose_output_path(app, surface_id, action_link, filedialog=fd)


def suggested_output_name(app, surface_id: str) -> str:
    return operation_paths.suggested_output_name(app, surface_id)


def current_merge_interaction(app, surface_id: str) -> dict | None:
    return operation_merge.current_merge_interaction(app, surface_id)


def merge_interaction_choices(app, surface_id: str) -> tuple[dict, ...]:
    return operation_merge.merge_interaction_choices(app, surface_id)


def _action_payload(app, surface_id: str, action_link: dict) -> dict | None:
    payload = {"action": str(action_link.get("action") or "")}
    payload.update(action_forms.read_action_payload(app, surface_id, action_link))
    fixed_payload = action_link.get("fixed_payload")
    if isinstance(fixed_payload, dict):
        payload.update(fixed_payload)
    dialog_payload = prompt_new_corpus_db_creation(app, surface_id, action_link, payload)
    if dialog_payload is None and isinstance(action_link.get("new_corpus_db_dialog"), dict):
        return None
    if isinstance(dialog_payload, dict):
        payload.update(dialog_payload)
    output_path = choose_output_path(app, surface_id, action_link)
    if action_link.get("requires_output_path") and output_path is None:
        return None
    if output_path is not None:
        payload["output_path"] = str(output_path)
    return payload


def _start_owner_action(app, surface_id: str, action_link: dict, target_root, contract_module: str, target_payload: dict, *, runtime) -> None:
    progress_handle = operation_progress.start(app, surface_id, action_link, target_payload)
    operation_state.action_loading(app).add(surface_id)
    token_name = f"operation:{surface_id}"
    token = background_jobs.next_token(app, token_name)
    if operation_state.has_async_ui(app):
        operation_state.rerender(app)
    background_jobs.start(
        app,
        work=lambda: invoke_module_contract(module_root=target_root, contract_module=contract_module, state_root=app._state_root, payload=target_payload),
        deliver=lambda result, error: _finish_surface_action(app, surface_id, action_link, token_name, token, result, error, progress_handle),
    )


def _finish_surface_action(app, surface_id: str, action_link: dict, token_name: str, token: int, result, error: Exception | None, progress_handle=None) -> None:
    operation_state.finish_surface_action(
        app,
        surface_id,
        action_link,
        token_name,
        token,
        result,
        error,
        progress_handle,
        background_jobs=background_jobs,
        operation_progress=operation_progress,
    )


def _runtime() -> SimpleNamespace:
    return SimpleNamespace(
        invoke_module_contract=invoke_module_contract,
        background_jobs=background_jobs,
        remember_result=operation_state.remember_result,
        rerender=operation_state.rerender,
        action_loading=operation_state.action_loading,
        has_async_ui=operation_state.has_async_ui,
    )


def _is_merge_action(action_link: dict) -> bool:
    return str(action_link.get("action") or "").strip() == "merge_corpus_databases"


def _write_merge_artifact(app, surface_id: str, interaction: dict, decision: str):
    return operation_merge.write_merge_artifact(app, surface_id, interaction, decision)


def _action_target(app, entry, action_link: dict, payload: dict):
    return operation_routing.action_target(app, entry, action_link, payload)
