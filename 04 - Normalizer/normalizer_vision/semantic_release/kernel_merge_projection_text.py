from __future__ import annotations

from typing import Any, Mapping, Sequence

_GENERIC_TEXTS = {"", "merged projection", "merged projection compiled from selected source projections.", "other"}


def merged_projection_label(
    source_payloads: Sequence[Mapping[str, Any]],
    master: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> str:
    docs = _term_labels(master, "document_types", payload.get("include_document_types"), limit=2)
    domains = _term_labels(master, "domains", payload.get("domain_ids"), limit=2)
    topics = _term_labels(master, "subcategories", payload.get("include_subcategories"), limit=1)
    if not topics:
        topics = _term_labels(master, "categories", payload.get("include_categories"), limit=1)
    parts = [_short_label_part(item) for item in [*domains[:1], *topics[:1], *docs]]
    if parts:
        return _fit_text(f"{' '.join(parts)} Projection", 96)
    source_labels = _source_texts(source_payloads, "label", limit=2)
    if source_labels:
        return _fit_label(f"{_join_phrase(source_labels)} Projection")
    return "Merged Projection"


def merged_projection_description(
    source_payloads: Sequence[Mapping[str, Any]],
    master: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> str:
    docs = _term_labels(master, "document_types", payload.get("include_document_types"), limit=3)
    domains = _term_labels(master, "domains", payload.get("domain_ids"), limit=3)
    topics = _term_labels(master, "subcategories", payload.get("include_subcategories"), limit=4)
    if not topics:
        topics = _term_labels(master, "categories", payload.get("include_categories"), limit=4)
    fields = _term_labels(master, "field_codes", payload.get("include_field_codes"), limit=5)
    rows = _term_labels(master, "row_types", payload.get("include_row_types"), limit=4)
    cells = _term_labels(master, "cell_codes", payload.get("include_cell_codes"), limit=4)

    sentences: list[str] = []
    if docs or domains:
        target = _join_phrase(docs) or "content"
        domain_text = f" in {_join_phrase(domains)}" if domains else ""
        sentences.append(f"Projection for {target}{domain_text}.")
    if topics:
        sentences.append(f"It covers {_join_phrase(topics)}.")
    materialized = []
    if fields:
        materialized.append(f"scalar fields such as {_join_phrase(fields)}")
    if rows:
        materialized.append(f"repeated rows such as {_join_phrase(rows)}")
    if cells:
        materialized.append(f"cells such as {_join_phrase(cells)}")
    if materialized:
        sentences.append(f"It normalizes {_join_phrase(materialized)}.")
    if not sentences:
        sentences.extend(_source_texts(source_payloads, "description", limit=2))
    return _compact_text(" ".join(sentences) or "Merged projection compiled from selected source projections.")


def merged_when_to_use(
    source_payloads: Sequence[Mapping[str, Any]],
    master: Mapping[str, Any],
    payload: Mapping[str, Any],
    routing: Mapping[str, Any] | None = None,
) -> str:
    docs = _term_labels(master, "document_types", payload.get("include_document_types"), limit=2)
    domains = _term_labels(master, "domains", payload.get("domain_ids"), limit=2)
    roles = _role_labels((routing or {}).get("section_roles") or payload.get("include_row_types"), limit=4)
    markers = _surface_markers(source_payloads, limit=4)
    boundary = _boundary_phrase(docs, domains)
    if boundary:
        base = f"Use for {boundary}."
    else:
        base = "Use when content matches the merged source projection boundary."
    extras: list[str] = []
    if roles:
        extras.append(f"Expected structures include {_join_phrase(roles)}")
    if markers:
        extras.append(f"typical markers include {_join_phrase(markers)}")
    if extras:
        base = f"{base} {'; '.join(extras)}."
    return _fit_text(base, 480)


def merged_avoid_when(
    source_payloads: Sequence[Mapping[str, Any]],
    master: Mapping[str, Any],
    payload: Mapping[str, Any],
    routing: Mapping[str, Any] | None = None,
) -> str:
    docs = _term_labels(master, "document_types", payload.get("include_document_types"), limit=2)
    domains = _term_labels(master, "domains", payload.get("domain_ids"), limit=2)
    roles = _role_labels((routing or {}).get("section_roles") or payload.get("include_row_types"), limit=3)
    boundary = _boundary_phrase(docs, domains)
    if boundary and roles:
        return _fit_text(f"Avoid when content does not match {boundary} or lacks {_join_phrase(roles)} structure.", 480)
    if boundary:
        return _fit_text(f"Avoid when content does not match {boundary}.", 480)
    source_ids = _source_texts(source_payloads, "projection_id", limit=2)
    if source_ids:
        return _fit_text(f"Avoid when content does not match {_join_phrase(source_ids)}.", 480)
    return "Avoid when content does not match the merged source projection boundary."


def _term_labels(master: Mapping[str, Any], section: str, codes: Any, *, limit: int) -> list[str]:
    index = _term_index(master.get(section))
    labels: list[str] = []
    for code in _texts(codes):
        if code == "other":
            continue
        item = index.get(code, {})
        label = _text(item.get("label")) or _humanize_code(code)
        if label.lower() not in _GENERIC_TEXTS:
            labels.append(label)
    return _dedupe(labels)[:limit]


def _term_index(items: Any) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    if isinstance(items, list):
        for item in items:
            if isinstance(item, Mapping) and (key := _text(item.get("code") or item.get("id") or item.get("slot"))):
                result[key] = item
    return result


def _source_texts(source_payloads: Sequence[Mapping[str, Any]], key: str, *, limit: int) -> list[str]:
    return _dedupe(
        text
        for payload in source_payloads
        if (text := _text(payload.get(key))) and text.lower() not in _GENERIC_TEXTS
    )[:limit]


def _surface_markers(source_payloads: Sequence[Mapping[str, Any]], *, limit: int) -> list[str]:
    markers: list[str] = []
    for payload in source_payloads:
        routing = payload.get("routing")
        signals = routing.get("surface_signals") if isinstance(routing, Mapping) else None
        if isinstance(signals, Mapping):
            markers.extend(_texts(signals.get("text_markers")))
    return _dedupe(markers)[:limit]


def _role_labels(value: Any, *, limit: int) -> list[str]:
    return [_humanize_code(item).lower() for item in _texts(value) if item != "other"][:limit]


def _boundary_phrase(docs: Sequence[str], domains: Sequence[str]) -> str:
    doc_text = _join_phrase(docs)
    domain_text = _join_phrase(domains)
    return f"{doc_text} in {domain_text}" if doc_text and domain_text else doc_text or domain_text


def _short_label_part(value: str) -> str:
    text = value.strip()
    for suffix in (" texts", " documents", " material", " content", " essay"):
        if text.lower().endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text.title()


def _join_phrase(values: Sequence[str]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if len(items) <= 1:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _fit_text(value: str, limit: int) -> str:
    text = _compact_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip(" .,;:-_") + "..."


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _humanize_code(value: str) -> str:
    return " ".join(part for part in value.replace("-", "_").split("_") if part).title()


def _texts(value: Any) -> list[str]:
    return [text for item in value if (text := _text(item))] if isinstance(value, list) else []


def _text(value: Any) -> str: return str(value or "").strip()


def _dedupe(values: Sequence[str] | Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result
