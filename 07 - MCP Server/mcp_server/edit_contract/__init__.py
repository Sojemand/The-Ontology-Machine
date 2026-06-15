"""Path-stable surface for the MCP Server edit contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..atomic_io import atomic_json_write
from . import validation, workflow
from .types import (
    DESCRIBE_SURFACES_ACTION,
    READ_BUNDLE_ACTION,
    READ_SURFACE_ACTION,
    SUPPORT_ACTIONS,
    VALIDATE_SURFACE_ACTION,
    WRITE_SURFACE_ACTION,
)

ROOT = Path(__file__).resolve().parents[2]


def _dispatch(payload: dict) -> dict:
    action = validation.require_action(payload)
    if action == DESCRIBE_SURFACES_ACTION:
        return workflow.describe(module_root=ROOT)
    if action == READ_BUNDLE_ACTION:
        return workflow.read_bundle(module_root=ROOT)
    if action in SUPPORT_ACTIONS:
        return workflow.run_support_action(action, payload, module_root=ROOT)
    surface_id = validation.require_surface_id(payload)
    if action == READ_SURFACE_ACTION:
        return workflow.read(surface_id, module_root=ROOT)
    if action == VALIDATE_SURFACE_ACTION:
        return workflow.validate(surface_id, validation.require_surface_value(payload), module_root=ROOT)
    if action == WRITE_SURFACE_ACTION:
        return workflow.write(surface_id, validation.require_surface_value(payload), module_root=ROOT)
    return workflow.error_response(f"Unbekannte Aktion: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover - defensive contract wrapper
        response = workflow.error_response(str(exc))
    _write_response(Path(args.response), response)
    return 0


def _load_request(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Request muss ein JSON-Objekt sein.")
    return payload


def _write_response(path: Path, payload: dict) -> None:
    atomic_json_write(path, payload, indent=2)


__all__ = ["ROOT", "main"]
