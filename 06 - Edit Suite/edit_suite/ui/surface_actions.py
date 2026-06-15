"""Save, validate and action-state helpers for the Edit Suite app surface."""

from __future__ import annotations

from ..surfaces import DraftState
from . import background_jobs


def action_button_state(app, surface_id: str) -> str:
    if (
        app.entry_is_loading()
        or surface_id in app._surface_action_loading_state()
        or surface_id in app._operation_action_loading_state()
    ):
        return "disabled"
    return "normal"


def apply_surface_action(app, surface_id: str, action, *, refresh_bundle: bool = False) -> None:
    entry = app._selected_entry()
    if entry is None:
        return
    try:
        value = app._read_widget_value(surface_id)
    except Exception as exc:
        _store_read_error(app, entry, surface_id, exc)
        return
    app._surface_action_loading_state().add(surface_id)
    token_name = f"surface:{entry.slot_name}:{surface_id}"
    token = background_jobs.next_token(app, token_name)
    loading_draft = DraftState(surface_id=surface_id, value=value, dirty=True, message="Loading...")
    app._drafts.setdefault(entry.slot_name, {})[surface_id] = loading_draft
    if app._has_async_ui():
        app._render_detail_only = True
        app._render()
    background_jobs.start(
        app,
        work=lambda: _run_surface_action(action, entry, DraftState(surface_id=surface_id, value=value, dirty=True), app._state_root),
        deliver=lambda result, error: app._finish_surface_action(
            token_name,
            token,
            entry,
            surface_id,
            result,
            error,
            refresh_bundle,
            value,
        ),
    )


def finish_surface_action(
    app,
    token_name: str,
    token: int,
    entry,
    surface_id: str,
    result,
    error: Exception | None,
    refresh_bundle: bool,
    value: dict,
) -> None:
    if not background_jobs.is_current(app, token_name, token):
        return
    app._surface_action_loading_state().discard(surface_id)
    if error is not None:
        updated = DraftState(surface_id=surface_id, value=value, dirty=True, message=f"Error: {error}")
    else:
        updated = result
        if refresh_bundle and not updated.dirty:
            app._remember_saved_draft(entry, updated)
            app._evict_bundle(entry)
            app._ensure_bundle(entry)
    app._drafts.setdefault(entry.slot_name, {})[surface_id] = updated
    app._render_detail_only = True
    app._render()


def _store_read_error(app, entry, surface_id: str, error: Exception) -> None:
    updated = DraftState(
        surface_id=surface_id,
        value=app._fallback_draft_value(surface_id),
        dirty=True,
        message=f"Error: {error}",
    )
    app._drafts.setdefault(entry.slot_name, {})[surface_id] = updated
    app._render_detail_only = True
    app._render()


def _run_surface_action(action, entry, draft: DraftState, state_root) -> DraftState:
    return action(entry, draft, state_root=state_root)
