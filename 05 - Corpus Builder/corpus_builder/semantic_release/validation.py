"""Hard validation boundaries for semantic release contracts."""
from __future__ import annotations

import sqlite3
from typing import Any

from .policy import build_release_fingerprint
from . import repository
from .policy import projection_metadata
from .shared_identity import resolve_master_taxonomy_release_id
from .types import ProjectionMetadata, ReleasePayload

REQUIRED_RELEASE_KEYS = {
    "release_id",
    "release_version",
    "master_taxonomy_id",
    "master_taxonomy_version",
    "projection_ids",
    "materialization_version",
    "fingerprint",
    "master_taxonomy",
    "projections",
}


def validate_release_payload(payload: dict[str, Any]) -> ReleasePayload:
    missing = sorted(REQUIRED_RELEASE_KEYS - set(payload))
    if missing:
        raise ValueError(f"Semantic Release unvollstaendig: {', '.join(missing)}")
    projection_ids = _require_projection_id_list(payload.get("projection_ids"), "projection_ids")
    if projection_ids != _canonical_projection_id_list(projection_ids):
        raise ValueError("projection_ids muss kanonisch nach projection_id sortiert sein.")
    found_projection_ids = [
        _validate_projection_payload(item, index)
        for index, item in enumerate(_require_list(payload.get("projections"), "projections"))
    ]
    if projection_ids and projection_ids != found_projection_ids:
        missing_ids = sorted(set(projection_ids) - set(found_projection_ids))
        extra_ids = sorted(set(found_projection_ids) - set(projection_ids))
        parts: list[str] = []
        if missing_ids:
            parts.append(f"fehlende Projection-Payloads: {', '.join(missing_ids)}")
        if extra_ids:
            parts.append(f"unerwartete Projection-Payloads: {', '.join(extra_ids)}")
        if not parts:
            parts.append("Projection-Payload-Reihenfolge muss projection_ids exakt entsprechen.")
        raise ValueError("Semantic Release Projection-Mismatch: " + "; ".join(parts))
    fingerprint = _require_text(payload.get("fingerprint"), "fingerprint")
    expected_fingerprint = build_release_fingerprint(payload)
    if fingerprint != expected_fingerprint:
        raise ValueError(f"fingerprint passt nicht zum Release-Inhalt: {fingerprint} != {expected_fingerprint}")
    release_fingerprint = str(payload.get("release_fingerprint") or "").strip()
    if release_fingerprint and release_fingerprint != fingerprint:
        raise ValueError("release_fingerprint passt nicht zum fingerprint.")
    if payload.get("master_taxonomy_release_id") not in (None, ""):
        _require_text(payload.get("master_taxonomy_release_id"), "master_taxonomy_release_id")
    else:
        resolve_master_taxonomy_release_id(payload)
    runtime_locale = payload.get("runtime_locale")
    if runtime_locale not in (None, ""):
        _require_text(runtime_locale, "runtime_locale")
    if str(payload.get("release_id") or "").strip() == "semantic_release.default":
        _validate_default_promotion_surface(payload)
    return payload  # type: ignore[return-value]


def validate_payload_against_release(payload: dict[str, Any], release: dict[str, Any]) -> ProjectionMetadata:
    projection_meta = projection_metadata(payload)
    projection_id = str(projection_meta.get("projection_id") or "").strip()
    if not projection_id:
        raise ValueError("normalized.json enthaelt keine projection_id.")
    release_master_id = str(release.get("master_taxonomy_id") or "").strip()
    input_master_id = str(projection_meta.get("master_taxonomy_id") or "").strip()
    if input_master_id and release_master_id and input_master_id != release_master_id:
        raise ValueError(
            f"Projection gehoert zu einer anderen Master-Taxonomie-Linie: {input_master_id} != {release_master_id}"
        )
    release_projection_ids = {
        str(value).strip()
        for value in release.get("projection_ids", []) or []
        if str(value).strip()
    }
    if projection_id not in release_projection_ids:
        raise ValueError(f"Projection im aktiven Release nicht gefunden: {projection_id}")
    return projection_meta


def assert_release_can_be_applied(conn: sqlite3.Connection, release: dict[str, Any]) -> None:
    compatibility = repository.inspect_release_application_compatibility(conn, release)
    errors: list[str] = []
    if compatibility["missing_projection_ids"]:
        sample = ", ".join(compatibility["missing_projection_ids"][:3])
        errors.append(
            f"{len(compatibility['missing_projection_ids'])} aktive Dokumente ohne projection_id "
            f"(Beispiele: {sample})"
        )
    if compatibility["foreign_master_ids"]:
        sample = ", ".join(compatibility["foreign_master_ids"][:3])
        errors.append(
            f"{len(compatibility['foreign_master_ids'])} aktive Dokumente aus einer anderen "
            f"Master-Taxonomie-Linie (Beispiele: {sample})"
        )
    if errors:
        raise ValueError("Semantic Release kann nicht angewendet werden: " + "; ".join(errors))


def _validate_projection_payload(payload: Any, index: int) -> str:
    projection = _require_dict(payload, f"projections[{index}]")
    projection_id = _require_text(projection.get("projection_id"), f"projections[{index}].projection_id")
    routing = _require_dict(projection.get("routing"), f"projections[{index}].routing")
    _require_text(routing.get("when_to_use"), f"projections[{index}].routing.when_to_use")
    _require_text(routing.get("avoid_when"), f"projections[{index}].routing.avoid_when")
    examples = _require_list(routing.get("example_document_types"), f"projections[{index}].routing.example_document_types")
    if not [_require_text(item, f"projections[{index}].routing.example_document_types[]") for item in examples]:
        raise ValueError(f"projections[{index}].routing.example_document_types darf nicht leer sein.")
    _require_dict(routing.get("surface_signals"), f"projections[{index}].routing.surface_signals")
    return projection_id


def _validate_default_promotion_surface(payload: dict[str, Any]) -> None:
    master = _require_dict(payload.get("master_taxonomy"), "master_taxonomy")
    slots = _require_list(master.get("promotion_slots"), "master_taxonomy.promotion_slots")
    if not slots:
        raise ValueError("Canonical Default Semantic Release enthaelt keine promotion_slots.")
    slot_names: set[str] = set()
    for index, item in enumerate(slots):
        slot = _require_text(
            _require_dict(item, f"master_taxonomy.promotion_slots[{index}]").get("slot"),
            f"master_taxonomy.promotion_slots[{index}].slot",
        )
        slot_names.add(slot)
    for projection_index, item in enumerate(_require_list(payload.get("projections"), "projections")):
        projection = _require_dict(item, f"projections[{projection_index}]")
        projection_id = str(projection.get("projection_id") or f"projections[{projection_index}]").strip()
        rules = _require_list(projection.get("promotion_rules"), f"{projection_id}.promotion_rules")
        if not rules:
            raise ValueError(f"Canonical Default Semantic Release Projection hat keine promotion_rules: {projection_id}")
        for rule_index, rule_item in enumerate(rules):
            rule = _require_dict(rule_item, f"{projection_id}.promotion_rules[{rule_index}]")
            slot = _require_text(rule.get("slot"), f"{projection_id}.promotion_rules[{rule_index}].slot")
            if slot not in slot_names:
                raise ValueError(
                    f"{projection_id}.promotion_rules[{rule_index}].slot ist nicht im Promotion Slot Registry: {slot}"
                )
            source_paths = _require_list(
                rule.get("source_paths"),
                f"{projection_id}.promotion_rules[{rule_index}].source_paths",
            )
            if not source_paths:
                raise ValueError(f"{projection_id}.promotion_rules[{rule_index}].source_paths darf nicht leer sein.")


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} muss ein JSON-Objekt sein.")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} muss eine Liste sein.")
    return value


def _require_projection_id_list(value: Any, label: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(_require_list(value, label)):
        projection_id = _require_text(item, f"{label}[{index}]")
        key = projection_id.casefold()
        if key in seen:
            raise ValueError(f"{label}[{index}] enthaelt eine doppelte Projection-ID.")
        seen.add(key)
        result.append(projection_id)
    return result


def _canonical_projection_id_list(values: list[str]) -> list[str]:
    return sorted(values, key=lambda item: (item.casefold(), item))


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} fehlt oder ist ungueltig.")
    return text
