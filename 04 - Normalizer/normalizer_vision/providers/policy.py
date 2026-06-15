"""Provider policy helpers for response-mode selection."""
from __future__ import annotations

from .payload import schema_supports_strict


def schema_mode(schema: dict[str, object] | None) -> str:
    if schema and schema_supports_strict(schema):
        return "json_schema"
    return "json_object"
