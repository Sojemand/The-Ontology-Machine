"""Edit-contract exports for the Interpreter module."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..models import atomic_json_write
from ..runtime_paths import resolve_runtime_paths
from . import validation, workflow
from .workflow import describe, error_response, read, read_bundle, validate, write
from .types import DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION

ROOT = Path(__file__).resolve().parents[2]


def _load_request(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Request muss ein JSON-Objekt sein.")
    return payload


def _write_response(path: Path, payload: dict) -> None:
    atomic_json_write(path, payload)


def _dispatch(payload: dict) -> dict:
    action = validation.require_action(payload)
    paths = resolve_runtime_paths()
    if action == DESCRIBE_SURFACES_ACTION:
        return workflow.describe(paths=paths, module_root=ROOT)
    if action == READ_BUNDLE_ACTION:
        return workflow.read_bundle(paths=paths, module_root=ROOT)
    surface_id = validation.require_surface_id(payload)
    if action == READ_SURFACE_ACTION:
        return workflow.read(surface_id, paths=paths, module_root=ROOT)
    if action == VALIDATE_SURFACE_ACTION:
        return workflow.validate(surface_id, validation.require_surface_value(payload))
    if action == WRITE_SURFACE_ACTION:
        return workflow.write(surface_id, validation.require_surface_value(payload), paths=paths)
    return workflow.error_response(f"Unbekannte Aktion: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover
        response = workflow.error_response(str(exc))
    _write_response(Path(args.response), response)
    return 0


__all__ = ["describe", "error_response", "main", "read", "read_bundle", "validate", "write"]
