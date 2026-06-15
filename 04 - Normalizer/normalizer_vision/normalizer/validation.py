"""Hard contract validation for model output payloads."""
from __future__ import annotations

import json
from typing import Any

from .types import ParsedModelOutput


def parse_model_output(response_text: str) -> ParsedModelOutput:
    data = load_model_output_object(response_text)
    return ParsedModelOutput(
        schema_version=_optional_string(data.get("schema_version")),
        processing=_required_dict_section(data, "processing"),
        classification=_required_dict_section(data, "classification"),
        context=_required_dict_section(data, "context"),
        content=_required_dict_section(data, "content"),
    )


def load_model_output_object(response_text: str) -> dict[str, Any]:
    data = json.loads(response_text)
    if not isinstance(data, dict):
        raise ValueError("Modellantwort muss ein JSON-Objekt sein")
    return data


def _required_dict_section(data: dict[str, Any], section: str) -> dict[str, Any]:
    if section not in data:
        raise ValueError(f"Modellantwort.{section} fehlt.")
    value = data[section]
    if not isinstance(value, dict):
        raise ValueError(f"Modellantwort.{section} muss ein JSON-Objekt sein.")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
