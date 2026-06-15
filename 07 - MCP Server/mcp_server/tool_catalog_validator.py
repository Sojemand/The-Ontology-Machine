from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool

_TIMEOUT_SECONDS = {
    "type": "integer",
    "minimum": 1,
    "maximum": 3600,
    "default": 120,
    "description": "MCP subprocess timeout; not forwarded as Validator product payload.",
}
_SURFACE_ID = {
    "type": "string",
    "description": "Validator edit-contract surface id, resolved by the owner contract.",
}
_SURFACE_VALUE = {
    "type": "object",
    "additionalProperties": True,
    "description": "Surface payload validated by 03 - Validator.",
}


def validator_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "validator.validate_document",
            "Validate exactly one structured.json and write one validation report by delegating exactly once to 03 - Validator validate_document. MCP bounds structured/raw/report paths and does not perform interpretation or JSON repair.",
            {
                "structured_root": {"type": "string", "description": "Existing root that must contain structured_path."},
                "structured_path": {"type": "string", "description": "Existing structured.json produced by the Interpreter stage."},
                "validation_root": {"type": "string", "description": "Existing root that must contain validation_output_path."},
                "validation_output_path": {"type": "string", "description": "Exact validation report target path for this Validator stage."},
                "raw_root": {"type": "string", "description": "Optional existing root that must contain raw_path when raw evidence is supplied."},
                "raw_path": {"type": "string", "description": "Optional raw evidence JSON for Validator checks; never used for interpretation."},
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("structured_root", "structured_path", "validation_root", "validation_output_path"),
        ),
        _tool(
            "validator.healthcheck",
            "Check Validator runtime and contract/config health through 03 - Validator healthcheck. MCP performs no validation work itself.",
            {
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
        ),
        _tool(
            "validator.describe_surfaces",
            "List Validator edit surfaces by delegating exactly once to 03 - Validator validator_vision.edit_contract. MCP does not keep a copied rule catalog.",
            {},
        ),
        _tool(
            "validator.read_surface",
            "Read exactly one Validator edit surface through 03 - Validator validator_vision.edit_contract.",
            {"surface_id": _SURFACE_ID},
            required=("surface_id",),
        ),
        _tool(
            "validator.validate_surface",
            "Validate exactly one Validator edit surface through 03 - Validator without writing.",
            {"surface_id": _SURFACE_ID, "value": _SURFACE_VALUE},
            required=("surface_id", "value"),
        ),
        _tool(
            "validator.write_surface",
            "Write exactly one Validator edit surface through 03 - Validator. The owner edit contract validates before persisting.",
            {"surface_id": _SURFACE_ID, "value": _SURFACE_VALUE},
            required=("surface_id", "value"),
        ),
    ]


__all__ = ["validator_tools"]
