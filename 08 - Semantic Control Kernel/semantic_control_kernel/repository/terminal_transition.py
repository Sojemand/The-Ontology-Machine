from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.errors import DuplicateStateObjectError

Validator = Callable[[Mapping[str, Any]], None]


def move_active_to_history(
    json_store: AtomicJsonStore,
    *,
    active_path: Path,
    history_path: Path,
    payload: Mapping[str, Any],
    validator: Validator,
    duplicate_message: str,
) -> None:
    copied = dict(payload)
    if history_path.exists():
        _reconcile_existing_history(
            json_store,
            active_path=active_path,
            history_path=history_path,
            payload=copied,
            validator=validator,
            duplicate_message=duplicate_message,
        )
        return
    try:
        json_store.write_json(history_path, copied, immutable=True, validator=validator)
    except DuplicateStateObjectError:
        _reconcile_existing_history(
            json_store,
            active_path=active_path,
            history_path=history_path,
            payload=copied,
            validator=validator,
            duplicate_message=duplicate_message,
        )
        return
    json_store.delete_json(active_path)


def _reconcile_existing_history(
    json_store: AtomicJsonStore,
    *,
    active_path: Path,
    history_path: Path,
    payload: Mapping[str, Any],
    validator: Validator,
    duplicate_message: str,
) -> None:
    existing = json_store.read_json(history_path, validator=validator)
    if not _same_terminal_payload(existing, payload):
        raise DuplicateStateObjectError(duplicate_message)
    json_store.delete_json(active_path)


def _same_terminal_payload(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_payload = dict(left)
    right_payload = dict(right)
    left_payload.pop("updated_at", None)
    right_payload.pop("updated_at", None)
    return left_payload == right_payload
