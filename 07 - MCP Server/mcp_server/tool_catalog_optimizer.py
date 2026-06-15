from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool


_OPTIMIZER_PROFILE = {
    "type": "string",
    "enum": ["vision", "file"],
    "description": "Optimizer profile owned by 01 - Optimizer.",
}
_FILTERS = {
    "type": "object",
    "properties": {
        "format": {"type": "string"},
        "doc_type": {"type": "string"},
        "max_size_mb": {"type": "integer", "minimum": 0},
        "batch_size": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}
_HASH_TOOLS = {
    "type": "object",
    "properties": {
        "use_processed_hashes": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
}
_TIMEOUT_SECONDS = {
    "type": "integer",
    "minimum": 1,
    "default": 120,
    "description": "MCP subprocess timeout; not forwarded as Optimizer product payload.",
}
_SURFACE_ID = {
    "type": "string",
    "description": "Optimizer edit-contract surface id, resolved by the owner contract.",
}
_SURFACE_VALUE = {
    "type": "object",
    "additionalProperties": True,
    "description": "Surface payload validated by 01 - Optimizer.",
}


def optimizer_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "optimizer.classify_document",
            "Classify one source document by delegating exactly once to 01 - Optimizer classify_document. MCP validates the input boundary and does not implement Optimizer routing logic.",
            {
                "source_path": {"type": "string"},
                "input_root": {"type": "string"},
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("source_path", "input_root"),
        ),
        _tool(
            "optimizer.extract_document",
            "Extract one source document to Optimizer raw output and page artifacts by delegating exactly once to 01 - Optimizer extract_document. The source, raw output and page image paths must stay inside declared input/output roots.",
            {
                "source_path": {"type": "string"},
                "input_root": {"type": "string"},
                "output_root": {"type": "string"},
                "raw_output_path": {"type": "string"},
                "page_images_dir": {"type": "string"},
                "logical_source_path": {"type": "string"},
                "optimizer_profile": _OPTIMIZER_PROFILE,
                "runtime_policy_path": {
                    "type": "string",
                    "description": "Required for optimizer_profile=vision; optional for optimizer_profile=file.",
                },
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=(
                "source_path",
                "input_root",
                "output_root",
                "raw_output_path",
                "page_images_dir",
                "logical_source_path",
                "optimizer_profile",
            ),
        ),
        _tool(
            "optimizer.healthcheck",
            "Check Optimizer runtime, plugins and profile dependencies through the owner contract. MCP only validates profile/dependency arguments.",
            {
                "optimizer_profile": _OPTIMIZER_PROFILE,
                "scope": {"type": "string", "description": "Optional Optimizer healthcheck scope such as pipeline_run."},
                "required_dependencies": {"type": "array", "items": {"type": "string"}},
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
        ),
        _tool(
            "optimizer.scan_debug_input",
            "Scan one Optimizer debug input folder and report what would be processed. MCP bounds the input root and debug session write root, then delegates to 01 - Optimizer scan_debug_input.",
            {
                "input_root": {"type": "string"},
                "debug_root": {"type": "string"},
                "session_root": {"type": "string"},
                "optimizer_profile": _OPTIMIZER_PROFILE,
                "filters": _FILTERS,
                "hash_tools": _HASH_TOOLS,
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("input_root", "debug_root", "session_root"),
        ),
        _tool(
            "optimizer.describe_surfaces",
            "List Optimizer edit surfaces by delegating exactly once to 01 - Optimizer ingestion_layer_vision.edit_contract. MCP does not keep a copied surface catalog.",
            {},
        ),
        _tool(
            "optimizer.read_surface",
            "Read exactly one Optimizer edit surface through 01 - Optimizer ingestion_layer_vision.edit_contract.",
            {"surface_id": _SURFACE_ID},
            required=("surface_id",),
        ),
        _tool(
            "optimizer.validate_surface",
            "Validate exactly one Optimizer edit surface through 01 - Optimizer without writing.",
            {"surface_id": _SURFACE_ID, "value": _SURFACE_VALUE},
            required=("surface_id", "value"),
        ),
        _tool(
            "optimizer.write_surface",
            "Write exactly one Optimizer edit surface through 01 - Optimizer. The owner edit contract validates before persisting.",
            {"surface_id": _SURFACE_ID, "value": _SURFACE_VALUE},
            required=("surface_id", "value"),
        ),
    ]


__all__ = ["optimizer_tools"]
