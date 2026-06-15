"""Path-stable surface for the Normalizer edit contract."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from ..orchestrator_contract import adapter
from ..paths import module_root
from ..source_authoring import operations as source_operations
from ..source_authoring import tools as source_tools
from . import validation, workflow
from .types import (
    DESCRIBE_SURFACES_ACTION,
    READ_BUNDLE_ACTION,
    READ_SURFACE_ACTION,
    SOURCE_OPERATION_ACTIONS,
    SOURCE_TOOL_ACTIONS,
    VALIDATE_SURFACE_ACTION,
    WRITE_SURFACE_ACTION,
)

ROOT = module_root()
APP_HOME: Path | None = None


def _dispatch(payload: dict) -> dict:
    action = validation.require_action(payload)
    body = validation.request_body(payload)
    env_home = os.getenv("NORMALIZER_VISION_HOME", "").strip()
    module_root_path = APP_HOME or (Path(env_home) if env_home else ROOT)
    if action == DESCRIBE_SURFACES_ACTION:
        return workflow.describe(module_root=module_root_path)
    if action == READ_BUNDLE_ACTION:
        return workflow.read_bundle(module_root=module_root_path)
    if action in SOURCE_TOOL_ACTIONS:
        return source_tools.dispatch(action, body, project_root=module_root_path)
    if action in SOURCE_OPERATION_ACTIONS:
        return source_operations.dispatch(action, body, project_root=module_root_path)
    surface_id = validation.require_surface_id(body)
    if action == READ_SURFACE_ACTION:
        return workflow.read(surface_id, module_root=module_root_path)
    if action == VALIDATE_SURFACE_ACTION:
        return workflow.validate(surface_id, validation.require_surface_value(body), module_root=module_root_path)
    if action == WRITE_SURFACE_ACTION:
        return workflow.write(surface_id, validation.require_surface_value(body), module_root=module_root_path)
    return workflow.error_response(f"Unbekannte Aktion: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    try:
        response = _dispatch(adapter.load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover - defensive
        response = workflow.error_response(str(exc))
    adapter.write_response(Path(args.response), response)
    return 0


__all__ = ["APP_HOME", "ROOT", "main", "validation", "workflow"]
