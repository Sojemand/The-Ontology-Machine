"""Pure content normalization logic for normalized outputs."""
from __future__ import annotations

from typing import Any

from ..taxonomy import TaxonomyProfile
from . import policy
from .row_domain import ROW_META_KEYS, normalize_rows
from .types import NormalizedContent

DATE_FIELD_CODES = {"document_date", "period_from", "period_to", "due_date"}


def normalize_content(
    *,
    profile: TaxonomyProfile,
    parsed_content: dict[str, Any],
    classification: dict[str, Any],
    context: dict[str, Any],
    notes: list[str],
) -> NormalizedContent:
    fields = _normalize_fields(profile, parsed_content.get("fields"), notes)
    rows = normalize_rows(profile, parsed_content.get("rows"), notes)
    structure = _normalize_structure(profile, parsed_content.get("structure"), fields, rows)
    free_text = _finalize_free_text(parsed_content.get("free_text"), classification, context, fields, rows)
    return NormalizedContent(structure=structure, fields=fields, rows=rows, free_text=free_text)


def _normalize_fields(
    profile: TaxonomyProfile,
    parsed_fields: Any,
    notes: list[str],
) -> dict[str, Any]:
    if not isinstance(parsed_fields, dict):
        return {}
    fields: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    for key, value in parsed_fields.items():
        if key == "_source_refs":
            continue
        canonical = profile.canonical_code("field", key, None)
        if canonical is None:
            extra[str(key)] = policy.normalize_output_value(value)
            continue
        if policy.is_empty_placeholder(value):
            continue
        if canonical in DATE_FIELD_CODES:
            fields[canonical] = policy.normalize_output_value(policy.normalize_iso_date(value))
            continue
        fields[canonical] = policy.normalize_output_value(value)
    if extra:
        notes.append(f"Dropped unknown field codes: {', '.join(sorted(extra))}.")
        if "other" in profile.field_codes:
            fields["other"] = extra
    return fields


def _normalize_structure(
    profile: TaxonomyProfile,
    parsed_structure: Any,
    fields: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    structure = parsed_structure if isinstance(parsed_structure, dict) else {}
    row_columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in ROW_META_KEYS and key not in row_columns:
                row_columns.append(key)
    parsed_columns: list[str] = []
    for value in structure.get("columns", []) if isinstance(structure.get("columns"), list) else []:
        canonical = profile.canonical_code("cell", value, None)
        if canonical and canonical not in parsed_columns:
            parsed_columns.append(canonical)
    form_fields = [key for key in fields if not key.startswith("_")]
    if not form_fields:
        raw_form_fields = structure.get("form_fields", []) if isinstance(structure.get("form_fields"), list) else []
        for value in raw_form_fields:
            canonical = profile.canonical_code("field", value, None)
            if canonical and canonical not in form_fields:
                form_fields.append(canonical)
    structure_type = policy.coerce_string(structure.get("type"))
    if structure_type is None:
        structure_type = "form_with_table" if form_fields and (row_columns or parsed_columns) else "text"
        if row_columns or parsed_columns:
            structure_type = "table" if not form_fields else structure_type
        elif form_fields:
            structure_type = "form"
    return {
        "type": structure_type,
        "columns": row_columns or parsed_columns,
        "form_fields": form_fields,
    }


def _finalize_free_text(
    model_free_text: Any,
    classification: dict[str, Any],
    context: dict[str, Any],
    fields: dict[str, Any],
    rows: list[dict[str, Any]],
) -> str:
    candidate = policy.coerce_string(model_free_text)
    if not candidate:
        return _build_free_text(classification, context, fields, rows)
    normalized_text = policy.collapse_whitespace(policy.normalize_dates_in_text(candidate))
    missing_prefixes = [
        value
        for key in ("document_type", "category", "subcategory")
        if isinstance((value := classification.get(key)), str) and value and value not in normalized_text
    ]
    if missing_prefixes:
        normalized_text = policy.collapse_whitespace(" ".join([*missing_prefixes, normalized_text]))
    return normalized_text


def _build_free_text(
    classification: dict[str, Any],
    context: dict[str, Any],
    fields: dict[str, Any],
    rows: list[dict[str, Any]],
) -> str:
    tokens: list[str] = []
    for key in ("document_type", "category", "subcategory"):
        value = classification.get(key)
        if isinstance(value, str) and value:
            tokens.append(value)
    for key in ("company", "document_title", "description", "document_date", "recipient_primary", "property_address"):
        tokens.extend(policy.flatten_tokens(context.get(key)))
    for key in ("tags", "people", "organizations", "locations", "currencies"):
        tokens.extend(policy.flatten_tokens(context.get(key)))
    if context.get("date_range"):
        tokens.extend(policy.flatten_tokens(context["date_range"]))
    if context.get("total_monetary_value") is not None:
        tokens.append(str(context["total_monetary_value"]))
    for key, value in fields.items():
        if key == "_source_refs":
            continue
        tokens.append(key)
        tokens.extend(policy.flatten_tokens(value))
    for row in rows:
        row_type = row.get("_row_type")
        if isinstance(row_type, str):
            tokens.append(row_type)
        units = row.get("_units", {}) if isinstance(row.get("_units"), dict) else {}
        for key, value in row.items():
            if key in ROW_META_KEYS:
                continue
            tokens.append(key)
            tokens.extend(policy.flatten_tokens(value))
            if key in units:
                tokens.append(str(units[key]))
    return policy.collapse_whitespace(" ".join(token for token in tokens if token))
