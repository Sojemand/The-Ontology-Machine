from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool

_MAX_OUTPUT_TOKENS = 200_000
_TIMEOUT_SECONDS = {
    "type": "integer",
    "minimum": 1,
    "maximum": 3600,
    "default": 120,
    "description": "MCP subprocess timeout; not forwarded as Interpreter product payload.",
}
_RUNTIME_SETTINGS = {
    "type": "object",
    "properties": {
        "model": {"type": "string", "description": "Provider model name owned by the Interpreter runtime settings."},
        "max_output_tokens": {
            "type": "integer",
            "minimum": 1,
            "maximum": _MAX_OUTPUT_TOKENS,
            "description": "Per-document output token ceiling passed to the Interpreter owner contract.",
        },
    },
    "required": ["model", "max_output_tokens"],
    "additionalProperties": False,
}


def interpreter_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "interpreter.interpret_document",
            "Interpret exactly one canonical Interpreter request into structured.json by delegating exactly once to 02 - Interpreter interpret_document. MCP bounds request/output paths and token settings but does not validate or repair structured JSON.",
            {
                "request_root": {"type": "string", "description": "Existing root that must contain request_path."},
                "request_path": {"type": "string", "description": "Canonical Interpreter request JSON for one document."},
                "output_root": {"type": "string", "description": "Existing root that must contain structured_output_path and optional debug_bundle_dir."},
                "structured_output_path": {"type": "string", "description": "Exact structured.json target path for this Interpreter stage."},
                "runtime_settings": _RUNTIME_SETTINGS,
                "debug_bundle_dir": {"type": "string", "description": "Optional Interpreter debug bundle folder inside output_root."},
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("request_root", "request_path", "output_root", "structured_output_path", "runtime_settings"),
        ),
        _tool(
            "interpreter.healthcheck",
            "Check Interpreter runtime and LLM-provider readiness through 02 - Interpreter healthcheck. MCP validates only the bounded runtime settings and reports the owner contract response.",
            {
                "runtime_settings": _RUNTIME_SETTINGS,
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("runtime_settings",),
        ),
        _tool(
            "interpreter.describe_surfaces",
            "Describe Interpreter edit surfaces by delegating exactly once to llm_interpreter.edit_contract describe_surfaces. MCP keeps no prompt, provider, schema, or credential truth.",
            {},
        ),
        _tool(
            "interpreter.read_surface",
            "Read exactly one Interpreter edit surface through llm_interpreter.edit_contract. No arbitrary source path or credential surface is accepted by MCP.",
            {"surface_id": {"type": "string"}},
            required=("surface_id",),
        ),
        _tool(
            "interpreter.validate_surface",
            "Validate exactly one Interpreter surface value through the owner edit contract without writing.",
            {"surface_id": {"type": "string"}, "value": {"type": "object"}},
            required=("surface_id", "value"),
        ),
        _tool(
            "interpreter.write_surface",
            "Write exactly one Interpreter surface through the owner edit contract; owner-local validation remains mandatory before persistence.",
            {"surface_id": {"type": "string"}, "value": {"type": "object"}},
            required=("surface_id", "value"),
        ),
    ]


__all__ = ["interpreter_tools"]
