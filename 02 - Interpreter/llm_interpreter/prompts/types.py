"""Prompt-facing types and output templates."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, TypedDict


class LoadedPageAsset(TypedDict):
    page: int
    path: Path
    media_type: str
    bytes: bytes


INTERPRETER_PROFILE = "vision"


MODEL_OUTPUT_TEMPLATE: dict[str, Any] = {
    "schema_version": "1.0",
    "processing": {
        "interpreter_profile": INTERPRETER_PROFILE,
        "model_confidence": 0.0,
        "needs_review": False,
        "review_reason": None,
        "vision_used": True,
    },
    "classification": {
        "document_type": "other",
        "document_type_confidence": 0.0,
        "category": "other",
        "subcategory": None,
        "language": "de",
        "is_scan": True,
        "has_handwriting": False,
        "page_count": 1,
    },
    "context": {
        "company": None,
        "document_date": None,
        "document_title": None,
        "description": None,
        "tags": [],
        "people": [],
        "organizations": [],
        "locations": [],
        "date_range": {"from": None, "to": None},
        "currencies": [],
        "total_monetary_value": None,
        "projection_hint": {
            "projection_id": None,
            "confidence": 0.0,
            "reason": None,
            "matched_signals": [],
        },
    },
    "content": {
        "structure": {"type": "mixed", "columns": [], "form_fields": []},
        "fields": {},
        "rows": [],
        "segments": [],
        "free_text": None,
    },
}

OUTPUT_TEMPLATE: dict[str, Any] = deepcopy(MODEL_OUTPUT_TEMPLATE)


__all__ = [
    "INTERPRETER_PROFILE",
    "LoadedPageAsset",
    "MODEL_OUTPUT_TEMPLATE",
    "OUTPUT_TEMPLATE",
]
