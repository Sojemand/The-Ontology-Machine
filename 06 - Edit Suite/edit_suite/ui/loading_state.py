"""Mutable loading-state helpers for the Edit Suite UI."""

from __future__ import annotations


def failed_slots(app) -> set[str]:
    try:
        state = object.__getattribute__(app, "__dict__")
    except AttributeError:
        return set()
    slots = state.get("_bundle_failed_slots")
    if isinstance(slots, set):
        return slots
    slots = set(slots) if isinstance(slots, (list, tuple, set)) else set()
    state["_bundle_failed_slots"] = slots
    return slots
