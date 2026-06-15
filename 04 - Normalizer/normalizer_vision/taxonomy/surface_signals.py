"""Validation helpers for projection-owned routing surface signals."""
from __future__ import annotations

from typing import Any

_SURFACE_SIGNAL_KEYS = ("text_markers", "domain_markers", "section_roles", "party_roles")


def default_surface_signals() -> dict[str, object]:
    return {
        "text_markers": [],
        "domain_markers": {},
        "section_roles": [],
        "party_roles": [],
    }


def projection_surface_signals(
    projection: dict[str, Any],
    *,
    required: bool,
    field_name: str = "routing.surface_signals",
) -> dict[str, object]:
    routing = projection.get("routing")
    if not isinstance(routing, dict):
        if required:
            raise ValueError(f"{field_name.rsplit('.', 1)[0]} muss ein JSON-Objekt sein.")
        return default_surface_signals()
    payload = routing.get("surface_signals")
    if payload is None and not required:
        return default_surface_signals()
    return normalize_surface_signals(
        payload,
        projection_id=str(projection.get("projection_id") or "").strip() or "<unknown>",
        domain_ids=list(projection.get("domain_ids") or []),
        field_name=field_name,
    )


def normalize_surface_signals(
    payload: Any,
    *,
    projection_id: str,
    domain_ids: list[str],
    field_name: str = "routing.surface_signals",
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(f"{field_name} muss ein JSON-Objekt sein.")
    missing = sorted(key for key in _SURFACE_SIGNAL_KEYS if key not in payload)
    unknown = sorted(str(key) for key in payload if key not in _SURFACE_SIGNAL_KEYS)
    if missing or unknown:
        parts: list[str] = []
        if missing:
            parts.append(f"fehlende Felder: {', '.join(missing)}")
        if unknown:
            parts.append(f"unbekannte Felder: {', '.join(unknown)}")
        raise ValueError(f"{field_name} ist ungueltig ({'; '.join(parts)}).")
    normalized = {
        "text_markers": _text_list(payload.get("text_markers"), label=f"{field_name}.text_markers"),
        "domain_markers": _domain_markers(
            payload.get("domain_markers"),
            label=f"{field_name}.domain_markers",
            allowed_domain_ids=domain_ids,
        ),
        "section_roles": _text_list(payload.get("section_roles"), label=f"{field_name}.section_roles"),
        "party_roles": _text_list(payload.get("party_roles"), label=f"{field_name}.party_roles"),
    }
    if not _has_any_markers(normalized):
        raise ValueError(f"{projection_id}.{field_name} darf nicht leer sein.")
    return normalized


def _domain_markers(payload: Any, *, label: str, allowed_domain_ids: list[str]) -> dict[str, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    allowed = {str(domain_id).strip() for domain_id in allowed_domain_ids if str(domain_id).strip()}
    unknown = sorted(str(key).strip() for key in payload if str(key).strip() not in allowed)
    if unknown:
        raise ValueError(f"{label} enthaelt unbekannte Keys: {', '.join(unknown)}")
    normalized: dict[str, list[str]] = {}
    for raw_key, raw_value in payload.items():
        key = str(raw_key).strip()
        normalized[key] = _text_list(raw_value, label=f"{label}.{key}", allow_empty=False)
    return normalized


def _text_list(payload: Any, *, label: str, allow_empty: bool = True) -> list[str]:
    if not isinstance(payload, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    values: list[str] = []
    seen: set[str] = set()
    for item in payload:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        values.append(text)
    if not allow_empty and not values:
        raise ValueError(f"{label} darf nicht leer sein.")
    return values


def _has_any_markers(payload: dict[str, object]) -> bool:
    text_markers = list(payload.get("text_markers") or [])
    domain_markers = dict(payload.get("domain_markers") or {})
    section_roles = list(payload.get("section_roles") or [])
    party_roles = list(payload.get("party_roles") or [])
    return bool(text_markers or section_roles or party_roles or any(domain_markers.values()))
