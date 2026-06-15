"""Path-stable surface for the Normalizer Vision subprocess contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..paths import MODULE_ROOT
from . import adapter, validation, workflow

ROOT = MODULE_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)

    try:
        response = workflow.dispatch(
            adapter.load_request(Path(args.request)),
            root=ROOT,
            require_action_fn=validation.require_action,
            parse_normalize_document_command_fn=validation.parse_normalize_document_command,
            parse_healthcheck_command_fn=validation.parse_healthcheck_command,
            parse_build_runtime_semantic_assets_command_fn=validation.parse_build_runtime_semantic_assets_command,
            parse_publish_semantic_release_command_fn=validation.parse_publish_semantic_release_command,
            parse_list_default_blueprints_command_fn=validation.parse_list_default_blueprints_command,
            parse_export_default_blueprint_release_command_fn=validation.parse_export_default_blueprint_release_command,
            parse_create_zero_shot_working_release_command_fn=validation.parse_create_zero_shot_working_release_command,
            parse_debug_run_command_fn=validation.parse_debug_run_command,
        )
    except Exception as exc:  # pragma: no cover - defensive
        response = workflow.error_response(str(exc))
    adapter.write_response(Path(args.response), response)
    return 0


__all__ = ["ROOT", "adapter", "main", "validation", "workflow"]
