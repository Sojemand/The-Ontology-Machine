"""Pure domain builders for semantic release entities, attributes, and audits."""
from __future__ import annotations

import json
import re
from typing import Any

from .policy import _normalize_text
from .types import MaterializationInputs


def build_entity_record(
    entity_key: str,
    entity_type: str,
    role_type: str | None,
    display_value: Any,
    source_path: str,
    inputs: MaterializationInputs,
    *,
    row_index: int | None = None,
) -> dict[str, Any]:
    return {
        "entity_key": entity_key,
        "entity_type": entity_type,
        "role_type": role_type,
        "display_value": None if display_value is None else str(display_value),
        "normalized_value": _normalize_text(display_value),
        "source_path": source_path,
        "row_index": row_index,
        "projection_id": inputs.projection_meta["projection_id"],
        "materialization_version": inputs.materialization_version,
        "state": "materialized",
    }


def build_attribute_record(entity_key: str, attribute_code: str, value: Any, source_path: str) -> dict[str, Any]:
    return {
        "entity_key": entity_key,
        "attribute_code": attribute_code,
        "display_value": None if value is None else str(value),
        "normalized_value": _normalize_text(value),
        "numeric_value": value if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
        "date_value": value if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None,
        "value_json": json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else None,
        "source_path": source_path,
    }


def build_missing_binding_audit(document_id: str, projection_id: str, field_code: str) -> dict[str, Any]:
    return {
        "level": "warn",
        "code": "missing_field_binding",
        "projection_id": projection_id,
        "document_id": document_id,
        "message": f"Feldcode ohne semantic_binding: {field_code}",
        "details_json": json.dumps({"field_code": field_code}, ensure_ascii=False),
    }


def build_fingerprint_audit(
    document_id: str,
    projection_id: str,
    input_fingerprint: str,
    release_fingerprint: str,
) -> dict[str, Any]:
    return {
        "level": "warn",
        "code": "projection_fingerprint_mismatch",
        "projection_id": projection_id,
        "document_id": document_id,
        "message": "Dokument wurde mit einer abweichenden Projection-Version normalisiert.",
        "details_json": json.dumps(
            {
                "input_projection_fingerprint": input_fingerprint,
                "active_projection_fingerprint": release_fingerprint,
            },
            ensure_ascii=False,
        ),
    }
