"""Path-stable surface for the Edit Suite subprocess contract."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..bootstrap import ensure_startup_prerequisites
from ..registry import discover_registry
from . import adapter, validation, workflow
from .types import HEALTHCHECK_ACTION


def _load_request(path: Path) -> dict:
    return adapter.load_request(path)


def _write_response(path: Path, payload: dict) -> None:
    adapter.write_response(path, payload)


def _error(message: str) -> dict:
    return workflow.error_response(message)


def _healthcheck(_payload: dict) -> dict:
    return workflow.healthcheck(
        ensure_startup_prerequisites=ensure_startup_prerequisites,
        discover_registry=discover_registry,
    )


def _dispatch(payload: dict) -> dict:
    try:
        action = validation.require_action(payload)
    except ValueError as exc:
        return _error(str(exc))
    if action == HEALTHCHECK_ACTION:
        return _healthcheck(payload)
    return _error(f"Unknown action: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover
        response = _error(str(exc))
    _write_response(Path(args.response), response)
    return 0


__all__ = ["HEALTHCHECK_ACTION", "ensure_startup_prerequisites", "main"]
