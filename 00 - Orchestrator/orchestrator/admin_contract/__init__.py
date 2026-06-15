"""Path-stable admin contract for orchestrator-owned runtime state."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..bootstrap import ORCHESTRATOR_ROOT
from ..orchestrator_contract import adapter
from . import validation, workflow
from .types import (
    INSPECT_RUNTIME_ACTION,
    MANAGE_CREDENTIALS_ACTION,
    MANAGE_RUNTIME_SETTINGS_ACTION,
    REVEAL_SECRET_ACTION,
)


def _dispatch(payload: dict) -> dict:
    try:
        action = validation.require_action(payload)
        if action == INSPECT_RUNTIME_ACTION:
            return workflow.inspect_runtime(root=ORCHESTRATOR_ROOT)
        if action == MANAGE_RUNTIME_SETTINGS_ACTION:
            return workflow.manage_runtime_settings(
                validation.runtime_settings_command(payload),
                root=ORCHESTRATOR_ROOT,
            )
        if action == MANAGE_CREDENTIALS_ACTION:
            return workflow.manage_credentials(
                validation.credentials_command(payload),
                root=ORCHESTRATOR_ROOT,
            )
        if action == REVEAL_SECRET_ACTION:
            return workflow.reveal_secret(validation.reveal_secret_command(payload), root=ORCHESTRATOR_ROOT)
        return workflow.error_response(f"Unknown admin action: {action}")
    except Exception as exc:
        return workflow.error_response(str(exc))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    response = _dispatch(adapter.load_request(Path(args.request)))
    adapter.write_response(Path(args.response), response)
    return 0


__all__ = ["ORCHESTRATOR_ROOT", "_dispatch", "adapter", "main", "validation", "workflow"]
