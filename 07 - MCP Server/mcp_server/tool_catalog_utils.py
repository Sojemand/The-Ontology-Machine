from __future__ import annotations

from typing import Any


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    *,
    required: tuple[str, ...] = (),
    output_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition = {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
    }
    if output_schema is not None:
        definition["outputSchema"] = output_schema
    return definition
def _enum(values: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": values}


def _artifact_properties(*, include_corpus_db: bool = True) -> dict[str, Any]:
    props = {
        "pipeline_root": {"type": "string"},
        "normalized_dir": {"type": "string"},
        "structured_dir": {"type": "string"},
        "validation_dir": {"type": "string"},
        "raw_dir": {"type": "string"},
    }
    if include_corpus_db:
        props["corpus_db_path"] = {"type": "string"}
    return props

__all__ = ["_tool", "_enum", "_artifact_properties"]
