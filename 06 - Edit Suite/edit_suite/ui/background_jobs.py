"""Threaded helpers that marshal results back onto the Tk thread."""

from __future__ import annotations

import threading
from typing import Callable


def _state_dict(app) -> dict:
    try:
        state = object.__getattribute__(app, "__dict__")
    except AttributeError:
        return {}
    return state if isinstance(state, dict) else {}


def next_token(app, name: str) -> int:
    tokens = _state_dict(app).get("_request_tokens")
    if not isinstance(tokens, dict):
        tokens = {}
        _state_dict(app)["_request_tokens"] = tokens
    token = int(tokens.get(name, 0)) + 1
    tokens[name] = token
    return token


def is_current(app, name: str, token: int) -> bool:
    tokens = _state_dict(app).get("_request_tokens", {})
    return int(tokens.get(name, 0)) == token


def start(app, *, work: Callable[[], object], deliver: Callable[[object | None, Exception | None], None]) -> None:
    scheduler = getattr(app, "after", None) if _has_async_scheduler(app) else None

    def runner() -> None:
        result = None
        error = None
        try:
            result = work()
        except Exception as exc:  # pragma: no cover - exercised through deliver callbacks
            error = exc
        _deliver(app, lambda: deliver(result, error))

    if not callable(scheduler):
        runner()
        return

    threading.Thread(target=runner, daemon=True).start()


def _deliver(app, callback: Callable[[], None]) -> None:
    scheduler = getattr(app, "after", None) if _has_async_scheduler(app) else None
    if callable(scheduler):
        scheduler(0, callback)
        return
    callback()


def _has_async_scheduler(app) -> bool:
    state = _state_dict(app)
    return bool(state.get("tk")) and callable(getattr(app, "after", None))
