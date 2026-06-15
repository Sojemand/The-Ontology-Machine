"""Shared state helpers for owner-action execution."""
from __future__ import annotations


def has_dirty_drafts(app, slot_name: str) -> bool:
    return any(bool(draft.dirty) for draft in app._drafts.get(slot_name, {}).values())


def remember_result(app, surface_id: str, action_link: dict, response: dict, **extra) -> None:
    state = {
        "label": str(action_link.get("label") or action_link.get("action") or "Action"),
        "contract_module": str(action_link.get("contract_module") or ""),
        "response": response,
    }
    state.update(extra)
    app._operation_results[surface_id] = state


def rerender(app) -> None:
    app._render_detail_only = True
    app._render()


def has_async_ui(app) -> bool:
    return bool(object.__getattribute__(app, "__dict__").get("tk")) and callable(getattr(app, "after", None))


def action_loading(app) -> set[str]:
    state = object.__getattribute__(app, "__dict__")
    loading = state.get("_operation_action_loading")
    if isinstance(loading, set):
        return loading
    loading = set(loading) if isinstance(loading, (list, tuple, set)) else set()
    state["_operation_action_loading"] = loading
    return loading


def finish_surface_action(
    app,
    surface_id: str,
    action_link: dict,
    token_name: str,
    token: int,
    result,
    error: Exception | None,
    progress_handle,
    *,
    background_jobs,
    operation_progress,
) -> None:
    if not background_jobs.is_current(app, token_name, token):
        return
    action_loading(app).discard(surface_id)
    if error is not None:
        response = {"status": "error", "reason": str(error)}
    else:
        response = result if isinstance(result, dict) else {"status": "error", "reason": "Invalid action response."}
    operation_progress.finish(progress_handle, response, error)
    remember_result(app, surface_id, action_link, response)
    rerender(app)
