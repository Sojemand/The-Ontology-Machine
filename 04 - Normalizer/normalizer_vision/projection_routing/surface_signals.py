"""Additive routing scores from release-owned surface signals."""
from __future__ import annotations

import re
from typing import Any

from ..taxonomy import TaxonomyProfile

_TEXT_MARKER_WEIGHT = 2
_DOMAIN_MARKER_WEIGHT = 3
_ROLE_WEIGHT = 1
_TEXT_MARKER_LIMIT = 4
_DOMAIN_MARKER_LIMIT = 3
_ROLE_LIMIT = 3
_SPACE_RE = re.compile(r"[\s_\-./:]+")


def score_surface_signals(profile: TaxonomyProfile, raw_doc: dict[str, Any]) -> tuple[int, list[str]]:
    surface_signals = dict(profile.surface_signals or {})
    if not surface_signals:
        return 0, []
    evidence = _collect_evidence(raw_doc)
    signals: list[str] = []
    score = _score_text_hits(
        evidence["text"],
        list(surface_signals.get("text_markers") or []),
        prefix="text_marker",
        weight=_TEXT_MARKER_WEIGHT,
        limit=_TEXT_MARKER_LIMIT,
        signals=signals,
    )
    score += _score_domain_hits(
        evidence["text"],
        evidence["domains"],
        dict(surface_signals.get("domain_markers") or {}),
        signals,
    )
    score += _score_role_hits(
        evidence["section_roles"],
        list(surface_signals.get("section_roles") or []),
        prefix="section_role",
        signals=signals,
    )
    score += _score_role_hits(
        evidence["party_roles"],
        list(surface_signals.get("party_roles") or []),
        prefix="party_role",
        signals=signals,
    )
    return score, signals


def _collect_evidence(raw_doc: dict[str, Any]) -> dict[str, object]:
    context = raw_doc.get("context") if isinstance(raw_doc.get("context"), dict) else {}
    content = raw_doc.get("content") if isinstance(raw_doc.get("content"), dict) else {}
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    text_parts = [
        context.get("document_title"),
        context.get("description"),
        content.get("free_text"),
    ]
    text_parts.extend(value for value in fields.values() if isinstance(value, str))
    for row in rows:
        if not isinstance(row, dict):
            continue
        text_parts.extend(value for key, value in row.items() if not str(key).startswith("_") and isinstance(value, str))
    return {
        "text": _normalize_text(" ".join(str(part).strip() for part in text_parts if str(part or "").strip())),
        "domains": _collect_domain_evidence(raw_doc),
        "section_roles": _collect_role_values(raw_doc, "section_roles"),
        "party_roles": _collect_role_values(raw_doc, "party_roles"),
    }


def _collect_domain_evidence(raw_doc: dict[str, Any]) -> set[str]:
    classification = raw_doc.get("classification") if isinstance(raw_doc.get("classification"), dict) else {}
    content = raw_doc.get("content") if isinstance(raw_doc.get("content"), dict) else {}
    fields = content.get("fields") if isinstance(content.get("fields"), dict) else {}
    rows = content.get("rows") if isinstance(content.get("rows"), list) else []
    evidence = {
        _normalize_token(classification.get("document_type")),
        _normalize_token(classification.get("category")),
        _normalize_token(classification.get("subcategory")),
    }
    evidence.update(_normalize_token(key) for key in fields)
    for row in rows:
        if not isinstance(row, dict):
            continue
        evidence.add(_normalize_token(row.get("_row_type")))
        evidence.update(_normalize_token(key) for key in row if not str(key).startswith("_"))
    evidence.update(_collect_role_values(raw_doc, "section_roles"))
    evidence.update(_collect_role_values(raw_doc, "party_roles"))
    return {value for value in evidence if value}


def _collect_role_values(raw_doc: dict[str, Any], role_key: str) -> set[str]:
    values: set[str] = set()
    for candidate in (
        raw_doc.get("layout_hints"),
        raw_doc.get("context"),
        (raw_doc.get("content") or {}).get("structure") if isinstance(raw_doc.get("content"), dict) else None,
    ):
        if not isinstance(candidate, dict):
            continue
        raw_roles = candidate.get(role_key)
        if not isinstance(raw_roles, list):
            continue
        for entry in raw_roles:
            role = entry.get("role") if isinstance(entry, dict) else entry
            normalized = _normalize_token(role)
            if normalized:
                values.add(normalized)
    return values


def _score_domain_hits(
    text: str,
    domains: set[str],
    domain_markers: dict[str, Any],
    signals: list[str],
) -> int:
    hits: list[str] = []
    for raw_domain, raw_markers in domain_markers.items():
        domain = _normalize_token(raw_domain)
        if not domain or domain not in domains:
            continue
        for marker in raw_markers if isinstance(raw_markers, list) else []:
            normalized_marker = _normalize_text(marker)
            if normalized_marker and _contains_marker(text, normalized_marker):
                hits.append(f"{domain}:{normalized_marker}")
    for item in hits[:_DOMAIN_MARKER_LIMIT]:
        signals.append(f"domain_marker:{item}")
    return len(hits[:_DOMAIN_MARKER_LIMIT]) * _DOMAIN_MARKER_WEIGHT


def _score_role_hits(
    evidence: set[str],
    candidates: list[Any],
    *,
    prefix: str,
    signals: list[str],
) -> int:
    hits = [role for role in (_normalize_token(item) for item in candidates) if role and role in evidence]
    for item in hits[:_ROLE_LIMIT]:
        signals.append(f"{prefix}:{item}")
    return len(hits[:_ROLE_LIMIT]) * _ROLE_WEIGHT


def _score_text_hits(
    text: str,
    candidates: list[Any],
    *,
    prefix: str,
    weight: int,
    limit: int,
    signals: list[str],
) -> int:
    hits = [marker for marker in (_normalize_text(item) for item in candidates) if marker and _contains_marker(text, marker)]
    for item in hits[:limit]:
        signals.append(f"{prefix}:{item}")
    return len(hits[:limit]) * weight


def _contains_marker(text: str, marker: str) -> bool:
    return bool(text and marker and f" {marker} " in f" {text} ")


def _normalize_text(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip().casefold()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_text(value).replace(" ", ".")
