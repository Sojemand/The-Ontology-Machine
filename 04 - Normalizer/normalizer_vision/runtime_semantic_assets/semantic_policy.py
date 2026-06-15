"""Compilation helpers for semantic extraction guardrail policies."""
from __future__ import annotations

from typing import Any

from ..taxonomy.surface_signals import projection_surface_signals
from .types import RuntimeSemanticPolicy

_POLICY_VERSION = "semantic_extraction_policy_v2"
_SOURCE_MODE = "release_projection_compile"
_DEFAULT_FALLBACK_ID = "housing.default.v1"
_COMMON_SECTION_ROLES = (
    "header",
    "summary",
    "body",
    "details",
    "table",
    "line_items",
    "billing",
    "payment",
    "notice",
    "timeline",
    "participants",
    "contact_block",
    "metadata",
    "vision_section",
    "ocr_chunk",
    "other",
)
_COMMON_FACT_FAMILIES = ("document", "reference", "counterparty", "money", "date", "payment", "contact", "other")
_ROW_ROLE_ALIASES = {
    "account_entry": "account_entries",
    "contact_block": "contact_block",
    "line_item": "line_items",
    "participant_list": "participants",
    "payment_schedule": "payment_schedule",
    "timeline_entry": "timeline",
}


def build_semantic_extraction_policy(
    release: dict[str, Any],
    *,
    fallback_projection_id: str | None = None,
) -> RuntimeSemanticPolicy:
    projections = [item for item in release.get("projections", []) or [] if isinstance(item, dict)]
    fallback_id = _resolve_fallback_projection_id(projections, fallback_projection_id=fallback_projection_id)
    default_projection = next(item for item in projections if str(item.get("projection_id") or "").strip() == fallback_id)
    return RuntimeSemanticPolicy(
        policy_version=_POLICY_VERSION,
        source_mode=_SOURCE_MODE,
        defaults={
            "fallback_projection_id": fallback_id,
            "resolution": _resolution_defaults(),
            "default_profile": _build_projection_profile(default_projection),
        },
        projection_overrides={
            projection_id: _build_projection_profile(projection)
            for projection in projections
            if (projection_id := str(projection.get("projection_id") or "").strip()) and projection_id != fallback_id
        },
    )


def _resolve_fallback_projection_id(
    projections: list[dict[str, Any]],
    *,
    fallback_projection_id: str | None,
) -> str:
    projection_ids = [str(item.get("projection_id") or "").strip() for item in projections if str(item.get("projection_id") or "").strip()]
    requested = str(fallback_projection_id or "").strip()
    if requested and requested in projection_ids:
        return requested
    if _DEFAULT_FALLBACK_ID in projection_ids:
        return _DEFAULT_FALLBACK_ID
    if projection_ids:
        return projection_ids[0]
    raise ValueError("semantic_extraction_policy benoetigt mindestens eine Projection.")


def _build_projection_profile(projection: dict[str, Any]) -> dict[str, Any]:
    projection_id = str(projection.get("projection_id") or "").strip()
    surface_signals = projection_surface_signals(projection, required=True)
    domain_ids = _dedupe_texts(_normalized_list(projection.get("domain_ids")))
    domains = _dedupe_texts(domain_ids + _normalized_list(projection.get("include_categories")))
    document_types = _dedupe_texts(
        _normalized_list(projection.get("include_document_types"))
        + _normalized_list((projection.get("routing") or {}).get("example_document_types"))
    )
    table_roles = _dedupe_texts(_normalized_table_roles(projection.get("include_row_types")))
    finance_profile = _is_finance_profile(domain_ids, document_types, projection_id)
    budgets = _budgets(finance_profile)
    return {
        "projection_id": projection_id,
        "signals": {
            "document_types": document_types,
            "field_labels": _dedupe_texts(_normalized_list(projection.get("include_field_codes"))),
            "table_roles": table_roles,
            "domains": domains,
            "text_markers": _dedupe_texts(_normalized_list(surface_signals.get("text_markers"))),
            "domain_markers": _normalized_domain_markers(surface_signals.get("domain_markers")),
            "section_roles": _dedupe_texts(_normalized_list(surface_signals.get("section_roles"))),
            "party_roles": _dedupe_texts(_normalized_list(surface_signals.get("party_roles"))),
        },
        "budgets": budgets,
        "allowed_section_roles": list(_COMMON_SECTION_ROLES),
        "allowed_synthetic_section_roles": ["header", "billing", "payment"] if finance_profile else ["header"],
        "allowed_fact_families": list(_COMMON_FACT_FAMILIES),
        "rescue_families": {
            "document_header": True,
            "invoice_financial": finance_profile,
            "payment": finance_profile,
        },
        "table_compaction": {
            "drop_text_only_rows": True,
            "max_rows_per_table": budgets["max_table_rows"],
        },
    }


def _resolution_defaults() -> dict[str, int]:
    return {
        "min_score": 7,
        "document_type_weight": 6,
        "field_weight": 1,
        "table_role_weight": 2,
        "field_signal_limit": 4,
        "table_signal_limit": 3,
    }


def _budgets(finance_profile: bool) -> dict[str, int]:
    return {
        "max_sections": 5 if finance_profile else 6,
        "max_section_chars": 700 if finance_profile else 850,
        "max_facts": 10 if finance_profile else 9,
        "max_tables": 2 if finance_profile else 1,
        "max_table_rows": 6 if finance_profile else 5,
    }


def _is_finance_profile(domains: list[str], document_types: list[str], projection_id: str) -> bool:
    if "finance" in domains:
        return True
    if projection_id.startswith("finance."):
        return True
    return any(item in {"invoice", "credit.note", "receipt", "payment.notice"} for item in document_types)


def _normalized_table_roles(value: Any) -> list[str]:
    roles = _normalized_list(value)
    expanded = [_ROW_ROLE_ALIASES.get(role, role) for role in roles]
    if "line_items" in expanded and "table" not in expanded:
        expanded.append("table")
    return expanded


def _normalized_domain_markers(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for raw_key, raw_value in value.items():
        key = _normalize_token(raw_key)
        markers = _dedupe_texts(_normalized_list(raw_value))
        if key and markers:
            normalized[key] = markers
    return normalized


def _normalized_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (_normalize_token(entry) for entry in value) if item]


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", ".").replace(" ", ".")


def _dedupe_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
