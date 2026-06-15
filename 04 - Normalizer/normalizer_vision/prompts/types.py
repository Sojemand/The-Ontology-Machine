"""Prompt-facing types and output templates."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PROMPT_FIELDS = (
    "system_prompt",
    "user_task_intro",
    "user_quality_rules",
    "output_schema",
)


@dataclass(frozen=True)
class PromptBundle:
    prompts: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str) -> str:
        return self.prompts.get(key, default)

    def output_schema_text(self, profile_id: str) -> str:
        custom = self.prompts.get("output_schema")
        if custom:
            return custom
        from .contract import build_default_output_schema_text

        return build_default_output_schema_text(profile_id)

    def to_payload(self) -> dict[str, str]:
        return {key: self.prompts.get(key, "") for key in PROMPT_FIELDS}


EMPTY_PROMPT_BUNDLE = PromptBundle()

MODEL_OUTPUT_TEMPLATE: dict[str, Any] = {
    "schema_version": "1.0",
    "processing": {
        "model_confidence": 0.0,
        "needs_review": False,
        "review_reason": None,
        "vision_used": False,
    },
    "classification": {
        "document_type": "other",
        "document_type_confidence": 0.0,
        "category": "other",
        "subcategory": "other",
        "language": "und",
        "is_scan": False,
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
        "taxonomy_profile_id": "housing.default.v1",
        "raw_classification": {},
        "normalization_notes": [],
    },
    "content": {
        "structure": {"type": "mixed", "columns": [], "form_fields": []},
        "fields": {},
        "rows": [],
        "free_text": "",
    },
}

__all__ = ["EMPTY_PROMPT_BUNDLE", "MODEL_OUTPUT_TEMPLATE", "PROMPT_FIELDS", "PromptBundle"]
