"""State access helpers for the Edit Suite app surface."""

from __future__ import annotations


def state_dict(app) -> dict:
    return object.__getattribute__(app, "__dict__")


def has_async_ui(app) -> bool:
    return bool(state_dict(app).get("tk")) and callable(getattr(app, "after", None))


def action_widgets_state(app) -> dict[str, dict]:
    state = state_dict(app).get("_action_widgets")
    if isinstance(state, dict):
        return state
    state = {}
    state_dict(app)["_action_widgets"] = state
    return state


def private_set(app, name: str) -> set[str]:
    state = state_dict(app).get(name)
    if isinstance(state, set):
        return state
    state = set(state) if isinstance(state, (list, tuple, set)) else set()
    state_dict(app)[name] = state
    return state


def private_mapping(app, name: str) -> dict:
    state = state_dict(app).get(name)
    if isinstance(state, dict):
        return state
    state = {}
    state_dict(app)[name] = state
    return state


def evict_bundle(app, entry) -> None:
    slot_name = entry.slot_name
    private_mapping(app, "_bundles").pop(slot_name, None)
    private_mapping(app, "_bundle_errors").pop(slot_name, None)
    private_set(app, "_bundle_live_slots").discard(slot_name)
    private_set(app, "_bundle_failed_slots").discard(slot_name)
