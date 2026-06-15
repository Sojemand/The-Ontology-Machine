"""Hard validation for loader boundary inputs."""

from __future__ import annotations

from .types import JsonDict


def validate_structured_envelope(structured_json: JsonDict) -> None:
    for key in ("classification", "content", "source"):
        if not isinstance(structured_json.get(key), dict):
            raise ValueError(f"structured.json fehlt oder enthaelt keinen Objekt-Block '{key}'")


def validate_normalized_envelope(normalized_json: JsonDict) -> None:
    for key in ("classification", "context", "content"):
        if not isinstance(normalized_json.get(key), dict):
            raise ValueError(f"normalized.json fehlt oder enthaelt keinen Objekt-Block '{key}'")


def default_validation_report() -> JsonDict:
    return {"result": "unknown", "needs_review": False, "summary": {"total_issues": 0}, "issues": []}


__all__ = ["default_validation_report", "validate_normalized_envelope", "validate_structured_envelope"]
