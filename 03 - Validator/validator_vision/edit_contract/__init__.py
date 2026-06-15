"""Path-stable surface for the validator edit contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..models.report_io import atomic_json_write
from ..orchestrator_contract.adapter import load_request, write_response
from ..paths import ensure_app_layout, module_root
from . import validation, workflow
from .types import DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION

ROOT = module_root()
APP_HOME: Path | None = None


def _dispatch(payload: dict) -> dict:
    action = validation.require_action(payload)
    if action == DESCRIBE_SURFACES_ACTION:
        return workflow.describe(home_root=None, module_root=ROOT)
    if action == READ_BUNDLE_ACTION:
        home_root = ensure_app_layout(APP_HOME)
        return workflow.read_bundle(home_root=home_root, module_root=ROOT)
    surface_id = validation.require_surface_id(payload)
    if action == READ_SURFACE_ACTION:
        home_root = ensure_app_layout(APP_HOME)
        return workflow.read(surface_id, home_root=home_root, module_root=ROOT)
    if action == VALIDATE_SURFACE_ACTION:
        return workflow.validate(surface_id, validation.require_surface_value(payload))
    if action == WRITE_SURFACE_ACTION:
        home_root = ensure_app_layout(APP_HOME)
        return workflow.write(surface_id, validation.require_surface_value(payload), home_root=home_root)
    return workflow.error_response(f"Unbekannte Aktion: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    try:
        response = _dispatch(load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover - defensive
        response = workflow.error_response(str(exc))
    write_response(Path(args.response), response, atomic_write=atomic_json_write)
    return 0
