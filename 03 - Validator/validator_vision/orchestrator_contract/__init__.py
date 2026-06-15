"""Path-stable surface for the Validator Vision subprocess contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..models.config import load_config
from ..paths import module_root
from ..validator import DocumentValidator
from . import adapter, debug_workflow, validation, workflow
from .types import DEBUG_RUN_ACTION, VALIDATE_DOCUMENT_ACTION

ROOT = module_root()


def _load_request(path: Path) -> dict:
    return adapter.load_request(path)


def _write_response(path: Path, payload: dict) -> None:
    adapter.write_response(path, payload)


def _error(message: str) -> dict:
    return workflow.error_response(message)


def _required_string(payload: dict, key: str) -> str | None:
    return validation._required_string(payload, key)


def _validate_document(payload: dict) -> dict:
    try:
        command = validation.parse_validate_document_command(payload)
    except ValueError as exc:
        return _error(str(exc))
    return workflow.validate_document(
        command,
        load_config_fn=load_config,
        validator_cls=DocumentValidator,
    )


def _healthcheck(_payload: dict) -> dict:
    return workflow.healthcheck(load_config_fn=load_config)


def _debug_run(payload: dict) -> dict:
    try:
        command = validation.parse_debug_run_command(payload)
    except ValueError as exc:
        return _error(str(exc))
    return debug_workflow.run_debug(
        command,
        load_config_fn=load_config,
        validator_cls=DocumentValidator,
    )


def validate_document(payload: dict) -> dict:
    return _validate_document(payload)


def debug_run(payload: dict) -> dict:
    return _debug_run(payload)


def healthcheck() -> dict:
    return workflow.healthcheck(load_config_fn=load_config)


def _dispatch(payload: dict) -> dict:
    try:
        action = validation.require_action(payload)
    except ValueError as exc:
        return _error(str(exc))
    if action == VALIDATE_DOCUMENT_ACTION:
        return _validate_document(payload)
    if action == DEBUG_RUN_ACTION:
        return _debug_run(payload)
    return _healthcheck(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)

    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover - defensive
        response = _error(str(exc))
    _write_response(Path(args.response), response)
    return 0


__all__ = ["ROOT", "debug_run", "healthcheck", "main", "validate_document"]
