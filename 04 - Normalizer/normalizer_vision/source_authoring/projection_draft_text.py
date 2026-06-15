"""Text and lexicon handling for projection drafts."""
from __future__ import annotations

from typing import Any

from . import locale_views
from .review_support import keyword_phrases, normalize_text
from .projection_draft_values import (
    first_present,
    merge_unique,
    optional_domain_markers,
    optional_mapping,
    optional_string_list,
    optional_text,
    required_text,
)


def apply_text_draft(
    text_payload: dict[str, Any],
    payload: dict[str, Any],
    *,
    domain_ids: list[str],
    template_lexicon: dict[str, Any],
) -> None:
    label = required_text(payload.get("label"), label="label")
    description = required_text(payload.get("description"), label="description")
    when_to_use = required_text(payload.get("when_to_use"), label="when_to_use")
    avoid_when = required_text(payload.get("avoid_when"), label="avoid_when")
    text_payload["label"] = label
    text_payload["description"] = description
    text_payload["routing"]["when_to_use"] = when_to_use
    text_payload["routing"]["avoid_when"] = avoid_when
    lexicon_payload = optional_mapping(payload.get("routing_lexicon"), label="routing_lexicon")
    text_markers = optional_string_list(first_present(payload, lexicon_payload, "text_markers"), label="text_markers")
    if text_markers is None:
        text_markers = derive_text_markers(label, description, when_to_use, *(optional_string_list(payload.get("example_document_types"), label="example_document_types") or []))
    domain_markers = optional_domain_markers(first_present(payload, lexicon_payload, "domain_markers"), label="domain_markers")
    if not domain_markers:
        domain_markers = derive_domain_markers(domain_ids=domain_ids, primary_domain=optional_text(payload.get("primary_domain")), text_markers=text_markers, template_lexicon=template_lexicon)
    if not text_markers and not any(domain_markers.values()):
        raise ValueError("routing_lexicon darf nicht leer sein.")
    text_payload["routing_lexicon"] = {"text_markers": text_markers, "domain_markers": domain_markers}


def mirror_draft_text_to_other_locales(
    projection: dict[str, Any],
    payload: dict[str, Any],
    *,
    active_locale: str,
    domain_ids: list[str],
    available_locales: list[str],
) -> None:
    for locale in available_locales:
        if locale == active_locale:
            continue
        text_payload = projection["texts"].get(locale)
        if not isinstance(text_payload, dict):
            raise ValueError(f"{projection['core']['projection_id']}.texts.{locale} muss ein Objekt sein.")
        apply_text_draft(text_payload, payload, domain_ids=domain_ids, template_lexicon={})


def generated_files(projection_id: str, locales: list[str]) -> list[str]:
    return [f"projections/{projection_id}.core.yaml", *[f"projections/{projection_id}.text.{locale}.yaml" for locale in locales]]


def derive_text_markers(*values: str) -> list[str]:
    markers: list[str] = []
    seen: set[str] = set()
    for phrase in keyword_phrases(*values):
        token = normalize_text(phrase).replace(" ", "_")
        if not token or "_" in token or len(token) <= 2 or token in seen:
            continue
        seen.add(token)
        markers.append(token)
        if len(markers) >= 8:
            break
    return markers


def derive_domain_markers(
    *,
    domain_ids: list[str],
    primary_domain: str | None,
    text_markers: list[str],
    template_lexicon: dict[str, Any],
) -> dict[str, list[str]]:
    template_domain_markers = optional_mapping(template_lexicon.get("domain_markers"), label="template_lexicon.domain_markers")
    ordered_domains = merge_unique(list(domain_ids), [str(domain_id).strip() for domain_id in template_domain_markers if str(domain_id).strip()])
    if not ordered_domains:
        ordered_domains = [primary_domain] if primary_domain else []
    target_domain = primary_domain or (ordered_domains[0] if ordered_domains else "")
    markers = list(text_markers[:6])
    return {target_domain: markers} if target_domain and markers else {}


def available_locales(package: dict[str, Any]) -> list[str]:
    return locale_views.available_locales(package)
