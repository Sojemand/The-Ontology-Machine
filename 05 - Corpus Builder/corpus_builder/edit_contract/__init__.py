"""Path-stable surface for the Corpus Builder edit contract."""

from __future__ import annotations

import argparse

from ..context.policy import package_module_root
from ..orchestrator_contract import adapter
from . import validation, workflow
from .types import DESCRIBE_SURFACES_ACTION, READ_BUNDLE_ACTION, READ_SURFACE_ACTION, VALIDATE_SURFACE_ACTION, WRITE_SURFACE_ACTION

ROOT = package_module_root()


def _dispatch(payload: dict) -> dict:
    action = validation.require_action(payload)
    if action == DESCRIBE_SURFACES_ACTION:
        return workflow.describe(module_root=ROOT)
    if action == READ_BUNDLE_ACTION:
        return workflow.read_bundle(module_root=ROOT)
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
        response = _dispatch(adapter.load_request(args.request))
    except Exception as exc:  # pragma: no cover - defensive
        response = workflow.error_response(str(exc))
    adapter.write_response(args.response, response)
    return 0


__all__ = ["ROOT", "main"]
