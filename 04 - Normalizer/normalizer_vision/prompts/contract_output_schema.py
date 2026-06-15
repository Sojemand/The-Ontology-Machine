from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .types import MODEL_OUTPUT_TEMPLATE

OUTPUT_SCHEMA_PROFILE_TOKEN = "{{taxonomy_profile_id}}"

_OUTPUT_SCHEMA_EXAMPLE_PATCH: dict[str, Any] = {
    "processing": {"processed_at": "2026-03-23T10:15:00Z", "model": "gpt-5.4-mini", "provider": "openai"},
    "context": {
        "description": "Compact evidence-bound English semantic summary of the document function or topic and its strongest visible anchors.",
        "recipient_primary": None,
        "property_address": None,
        "raw_classification": {"document_type": None, "category": None, "subcategory": None},
    },
    "content": {
        "structure": {
            "type": "text|form|table|form_with_table|list|mixed",
            "columns": ["cell_code"],
            "form_fields": ["field_code"],
        },
        "fields": {"field_code": "value"},
        "rows": [
            {
                "_row_type": "row_type",
                "_row_index": 0,
                "cell_code": "compact row value",
            },
        ],
        "free_text": "compact retrieval text from canonical codes and values",
    },
}


def build_default_output_schema_text(profile_id: str) -> str:
    example = deepcopy(MODEL_OUTPUT_TEMPLATE)
    example["context"]["taxonomy_profile_id"] = profile_id
    _merge_patch(example, _OUTPUT_SCHEMA_EXAMPLE_PATCH)
    return json.dumps(example, indent=2, ensure_ascii=False)


def build_default_output_schema_template_text() -> str:
    return build_default_output_schema_text(OUTPUT_SCHEMA_PROFILE_TOKEN)


def render_output_schema_text(text: str, profile_id: str) -> str:
    return text.replace(OUTPUT_SCHEMA_PROFILE_TOKEN, profile_id)


def _merge_patch(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_patch(target[key], value)
            continue
        target[key] = deepcopy(value)
