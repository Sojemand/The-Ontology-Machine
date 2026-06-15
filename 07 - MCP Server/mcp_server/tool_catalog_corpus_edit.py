from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool

_SURFACE_ID = {
    "type": "string",
    "description": "Corpus Builder edit-contract surface id, resolved by the owner contract.",
}
_SURFACE_VALUE = {
    "type": "object",
    "additionalProperties": True,
    "description": "Surface payload validated by 05 - Corpus Builder.",
}


def corpus_edit_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "corpus_builder.describe_surfaces",
            "List Corpus Builder edit surfaces by delegating exactly once to 05 - Corpus Builder corpus_builder.edit_contract. MCP does not keep a copied surface catalog.",
            {},
        ),
        _tool(
            "corpus_builder.read_surface",
            "Read exactly one Corpus Builder edit surface through 05 - Corpus Builder corpus_builder.edit_contract.",
            {"surface_id": _SURFACE_ID},
            required=("surface_id",),
        ),
        _tool(
            "corpus_builder.validate_surface",
            "Validate exactly one Corpus Builder edit surface through 05 - Corpus Builder without writing.",
            {"surface_id": _SURFACE_ID, "value": _SURFACE_VALUE},
            required=("surface_id", "value"),
        ),
        _tool(
            "corpus_builder.write_surface",
            "Write exactly one Corpus Builder edit surface through 05 - Corpus Builder. The owner edit contract validates before persisting.",
            {"surface_id": _SURFACE_ID, "value": _SURFACE_VALUE},
            required=("surface_id", "value"),
        ),
    ]


__all__ = ["corpus_edit_tools"]
