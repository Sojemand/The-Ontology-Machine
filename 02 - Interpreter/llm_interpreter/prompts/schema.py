"""Strict JSON-schema helpers for the merged interpreter."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

_PROCESSING_REQUIRED = [
    "interpreter_profile",
    "model_confidence",
    "needs_review",
    "review_reason",
    "vision_used",
]

_PROCESSING_PROPERTIES: dict[str, Any] = {
    "interpreter_profile": {"type": "string", "enum": ["vision", "file"]},
    "model_confidence": {"type": "number"},
    "needs_review": {"type": "boolean"},
    "review_reason": {"type": ["string", "null"]},
    "vision_used": {"type": "boolean"},
    "processed_at": {"type": "string"},
    "model": {"type": "string"},
    "provider": {"type": "string"},
}

_SEGMENT_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "required": ["segment_id", "unit_kind", "page", "sequence", "text"],
    "properties": {
        "segment_id": {"type": "string"},
        "unit_kind": {"type": "string"},
        "page": {"type": "integer"},
        "sequence": {"type": "integer"},
        "section": {"type": ["string", "null"]},
        "label": {"type": ["string", "null"]},
        "text": {"type": "string"},
        "function": {"type": ["string", "null"]},
        "attributes": {"type": "object", "additionalProperties": True},
        "confidence": {"type": "number"},
    },
}

MODEL_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "processing", "classification", "context", "content"],
    "properties": {
        "schema_version": {"type": "string"},
        "processing": {
            "type": "object",
            "additionalProperties": False,
            "required": list(_PROCESSING_REQUIRED),
            "properties": dict(_PROCESSING_PROPERTIES),
        },
        "classification": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "document_type",
                "document_type_confidence",
                "category",
                "subcategory",
                "language",
                "is_scan",
                "has_handwriting",
                "page_count",
            ],
            "properties": {
                "document_type": {"type": "string"},
                "document_type_confidence": {"type": "number"},
                "category": {"type": "string"},
                "subcategory": {"type": ["string", "null"]},
                "language": {"type": "string"},
                "is_scan": {"type": "boolean"},
                "has_handwriting": {"type": "boolean"},
                "page_count": {"type": "integer"},
            },
        },
        "context": {"type": "object", "additionalProperties": True},
        "content": {
            "type": "object",
            "additionalProperties": False,
            "required": ["structure", "fields", "rows", "segments", "free_text"],
            "properties": {
                "structure": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["type", "columns", "form_fields"],
                    "properties": {
                        "type": {"type": "string"},
                        "columns": {"type": "array", "items": {"type": ["string", "object"]}},
                        "form_fields": {"type": "array", "items": {"type": ["string", "object"]}},
                    },
                },
                "fields": {"type": "object", "additionalProperties": True},
                "rows": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                "segments": {"type": "array", "items": _SEGMENT_ITEM_SCHEMA},
                "free_text": {"type": ["string", "null"]},
            },
        },
    },
}

STRUCTURED_OUTPUT_SCHEMA: dict[str, Any] = deepcopy(MODEL_OUTPUT_SCHEMA)
STRUCTURED_OUTPUT_SCHEMA["required"] = list(MODEL_OUTPUT_SCHEMA["required"]) + ["source"]
STRUCTURED_OUTPUT_SCHEMA["properties"]["source"] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["file_name", "file_path", "file_ext", "size_bytes", "content_hash", "created_at", "modified_at"],
    "properties": {
        "file_name": {"type": "string"},
        "file_path": {"type": "string"},
        "file_ext": {"type": "string"},
        "size_bytes": {"type": ["integer", "null"]},
        "content_hash": {"type": "string"},
        "created_at": {"type": ["string", "null"]},
        "modified_at": {"type": ["string", "null"]},
    },
}


def get_output_schema() -> dict[str, Any]:
    return deepcopy(MODEL_OUTPUT_SCHEMA)


def get_persisted_output_schema() -> dict[str, Any]:
    return deepcopy(STRUCTURED_OUTPUT_SCHEMA)


__all__ = ["get_output_schema", "get_persisted_output_schema"]
