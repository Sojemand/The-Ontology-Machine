"""Pure document-level normalization logic for envelope assembly."""
from __future__ import annotations

from typing import Any

from ..models.config import NormalizerExecutionConfig
from ..models.coercion import coerce_bool, coerce_float, coerce_int, dedupe_keep_order
from ..models.serialization import utc_now_iso
from ..projection_routing.types import ProjectionSelection
from ..taxonomy import TaxonomyProfile
from . import content as content_stage, policy
from .types import NormalizedEnvelope, ParsedModelOutput

FIXED_CONTEXT_KEYS = {
    "company",
    "document_date",
    "document_title",
    "description",
    "tags",
    "people",
    "organizations",
    "locations",
    "date_range",
    "currencies",
    "total_monetary_value",
    "taxonomy_profile_id",
    "raw_classification",
    "normalization_notes",
}


def build_normalized_envelope(
    *,
    config: NormalizerExecutionConfig,
    profile: TaxonomyProfile,
    raw_doc: dict[str, Any],
    parsed: ParsedModelOutput,
    provider_name: str,
    projection_selection: ProjectionSelection,
) -> NormalizedEnvelope:
    notes: list[str] = []
    raw_classification = _dict_or_empty(raw_doc.get("classification"))
    raw_context = _dict_or_empty(raw_doc.get("context"))
    classification = _normalize_classification(profile, parsed.classification, raw_classification, parsed.processing)
    raw_document_type = policy.coerce_string(raw_classification.get("document_type"))
    if raw_document_type and raw_document_type != classification["document_type"]:
        notes.append(f"Raw document_type '{raw_document_type}' normalized to '{classification['document_type']}'.")
    context = _normalize_context(parsed.context, raw_context, raw_classification, profile, notes)
    content = content_stage.normalize_content(
        profile=profile,
        parsed_content=parsed.content,
        classification=classification,
        context=context,
        notes=notes,
    )
    context["normalization_notes"] = dedupe_keep_order(context["normalization_notes"] + notes)
    processing = _normalize_processing(config, parsed.processing, classification, context["normalization_notes"], provider_name)
    return NormalizedEnvelope(
        schema_version=str(parsed.schema_version or raw_doc.get("schema_version") or "1.0"),
        processing=processing,
        classification=classification,
        context=context,
        content=content,
        projection=_build_projection_metadata(profile, projection_selection),
    )


def _normalize_classification(
    profile: TaxonomyProfile,
    parsed_classification: dict[str, Any],
    raw_classification: dict[str, Any],
    parsed_processing: dict[str, Any],
) -> dict[str, Any]:
    return {
        "document_type": profile.canonical_code("document_type", parsed_classification.get("document_type"), "other"),
        "document_type_confidence": coerce_float(
            parsed_classification.get("document_type_confidence"),
            coerce_float(parsed_processing.get("model_confidence"), 0.0),
        ),
        "category": profile.canonical_code("category", parsed_classification.get("category"), "other"),
        "subcategory": profile.canonical_code("subcategory", parsed_classification.get("subcategory"), "other"),
        "language": policy.coerce_string(parsed_classification.get("language"))
        or policy.coerce_string(raw_classification.get("language"))
        or "und",
        "is_scan": coerce_bool(parsed_classification.get("is_scan"), coerce_bool(raw_classification.get("is_scan"), False)),
        "has_handwriting": coerce_bool(
            parsed_classification.get("has_handwriting"),
            coerce_bool(raw_classification.get("has_handwriting"), False),
        ),
        "page_count": max(
            1,
            coerce_int(parsed_classification.get("page_count"), coerce_int(raw_classification.get("page_count"), 1)),
        ),
    }


def _normalize_context(
    parsed_context: dict[str, Any],
    raw_context: dict[str, Any],
    raw_classification: dict[str, Any],
    profile: TaxonomyProfile,
    notes: list[str],
) -> dict[str, Any]:
    date_range = parsed_context.get("date_range") if isinstance(parsed_context.get("date_range"), dict) else {}
    context: dict[str, Any] = {
        "company": policy.coerce_string(parsed_context.get("company")) or policy.coerce_string(raw_context.get("company")),
        "document_date": policy.normalize_iso_date(
            policy.coerce_string(parsed_context.get("document_date")) or policy.coerce_string(raw_context.get("document_date"))
        ),
        "document_title": policy.coerce_string(parsed_context.get("document_title"))
        or policy.coerce_string(raw_context.get("document_title")),
        "description": policy.coerce_string(parsed_context.get("description")) or policy.coerce_string(raw_context.get("description")),
        "tags": policy.string_list_with_fallback(parsed_context.get("tags"), raw_context.get("tags")),
        "people": policy.string_list_with_fallback(parsed_context.get("people"), raw_context.get("people")),
        "organizations": policy.string_list_with_fallback(parsed_context.get("organizations"), raw_context.get("organizations")),
        "locations": policy.string_list_with_fallback(parsed_context.get("locations"), raw_context.get("locations")),
        "date_range": {
            "from": policy.normalize_iso_date(policy.coerce_string(date_range.get("from"))),
            "to": policy.normalize_iso_date(policy.coerce_string(date_range.get("to"))),
        },
        "currencies": policy.string_list_with_fallback(parsed_context.get("currencies"), raw_context.get("currencies")),
        "total_monetary_value": policy.numeric_with_fallback(
            parsed_context.get("total_monetary_value"),
            raw_context.get("total_monetary_value"),
        ),
        "taxonomy_profile_id": profile.projection_id,
        "raw_classification": {key: raw_classification.get(key) for key in ("document_type", "category", "subcategory")},
        "normalization_notes": dedupe_keep_order(policy.string_list(parsed_context.get("normalization_notes")) + notes),
    }
    for key, value in parsed_context.items():
        if key in FIXED_CONTEXT_KEYS:
            continue
        try:
            context[key] = policy.normalize_output_value(value)
        except TypeError:
            context["normalization_notes"].append(f"Context key '{key}' konnte nicht serialisiert werden.")
    context["normalization_notes"] = dedupe_keep_order(policy.string_list(context["normalization_notes"]))
    return context


def _normalize_processing(
    config: NormalizerExecutionConfig,
    parsed_processing: dict[str, Any],
    classification: dict[str, Any],
    notes: list[str],
    provider_name: str,
) -> dict[str, Any]:
    explicit_needs_review = coerce_bool(parsed_processing.get("needs_review"), False)
    review_reason = policy.coerce_string(parsed_processing.get("review_reason"))
    processing = {
        "model_confidence": coerce_float(parsed_processing.get("model_confidence"), 0.0),
        "needs_review": explicit_needs_review,
        "review_reason": review_reason,
        "vision_used": False,
        "processed_at": utc_now_iso(),
        "model": config.model,
        "provider": provider_name,
    }
    processing["review_reason"] = policy.derive_review_reason(
        explicit_needs_review,
        review_reason,
        classification,
        notes,
    )
    processing["needs_review"] = bool(
        explicit_needs_review
        or processing["review_reason"]
        or policy.classification_requires_review(classification)
        or policy.notes_require_review(notes)
    )
    if not processing["needs_review"]:
        processing["review_reason"] = None
    return processing


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _build_projection_metadata(
    profile: TaxonomyProfile,
    projection_selection: ProjectionSelection,
) -> dict[str, Any]:
    projection = profile.projection_metadata()
    projection["selection"] = projection_selection.to_dict()
    return projection
