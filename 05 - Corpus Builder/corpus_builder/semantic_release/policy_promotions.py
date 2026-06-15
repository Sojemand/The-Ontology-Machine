from __future__ import annotations

from typing import Any

from .types import DocumentPromotion, SlotCandidate
from .policy_promotion_values import (
    _compact_text,
    _date_value,
    _display_value,
    _normalize_text,
    _numeric_value,
    _promotion_values,
    _resolve_path_segments,
    _resolve_segments,
    json_dumps,
)


def materialize_promotions(
    payload: dict[str, Any],
    projection: dict[str, Any],
    *,
    release_fingerprint: str,
    materialization_version: str,
) -> tuple[list[SlotCandidate], list[DocumentPromotion]]:
    candidates: list[SlotCandidate] = []
    promotions: list[DocumentPromotion] = []
    projection_id = str(projection.get("projection_id") or "unknown")
    slot_defs = _promotion_slot_defs(projection)
    promotion_index = 0
    for rule in projection.get("promotion_rules", []) or []:
        promotion_index = _collect_rule_promotions(
            candidates,
            promotions,
            payload,
            rule,
            slot_defs,
            projection_id,
            release_fingerprint,
            materialization_version,
            promotion_index,
        )
    return candidates, promotions


def _collect_rule_promotions(
    candidates: list[SlotCandidate],
    promotions: list[DocumentPromotion],
    payload: dict[str, Any],
    rule: Any,
    slot_defs: dict[str, dict[str, Any]],
    projection_id: str,
    release_fingerprint: str,
    materialization_version: str,
    promotion_index: int,
) -> int:
    if not isinstance(rule, dict):
        return promotion_index
    slot = str(rule.get("slot", "")).strip()
    if not slot:
        return promotion_index
    slot_def = slot_defs.get(slot, {"slot": slot, "value_type": "string", "cardinality": "single"})
    cardinality = str(slot_def.get("cardinality") or "single")
    ordinal = 0
    for source_path in rule.get("source_paths", []) or []:
        values = _promotion_values(_resolve_path_segments(payload, str(source_path)), cardinality=cardinality)
        for item in values:
            display_value = _display_value(item)
            if display_value is None:
                continue
            promotion = _promotion_record(
                slot=slot,
                slot_def=slot_def,
                display_value=display_value,
                raw_value=item,
                ordinal=ordinal,
                source_path=str(source_path),
                projection_id=projection_id,
                release_fingerprint=release_fingerprint,
                materialization_version=materialization_version,
                promotion_index=promotion_index,
            )
            promotions.append(promotion)
            candidates.append(_candidate_from_promotion(promotion, promotion_index=promotion_index))
            promotion_index += 1
            ordinal += 1
            if cardinality != "multi":
                return promotion_index
    return promotion_index


def _promotion_slot_defs(projection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in projection.get("promotion_slots", []) or []:
        if not isinstance(item, dict):
            continue
        slot = str(item.get("slot") or "").strip()
        if slot:
            result[slot] = item
    return result


def _promotion_record(
    *,
    slot: str,
    slot_def: dict[str, Any],
    display_value: str,
    raw_value: Any,
    ordinal: int,
    source_path: str,
    projection_id: str,
    release_fingerprint: str,
    materialization_version: str,
    promotion_index: int,
) -> DocumentPromotion:
    return {
        "slot": slot,
        "slot_label": slot_def.get("label"),
        "value_type": str(slot_def.get("value_type") or "string"),
        "query_role": slot_def.get("query_role"),
        "display_value": display_value,
        "normalized_value": _normalize_text(display_value),
        "compact_value": _compact_text(display_value),
        "numeric_value": _numeric_value(raw_value),
        "date_value": _date_value(raw_value),
        "value_json": json_dumps(raw_value) if isinstance(raw_value, (dict, list)) else None,
        "ordinal": ordinal,
        "confidence": 1.0,
        "source_path": source_path,
        "source_refs": [],
        "projection_id": projection_id,
        "release_fingerprint": release_fingerprint,
        "materialization_version": materialization_version,
        "promotion_index": promotion_index,
    }


def _candidate_from_promotion(promotion: DocumentPromotion, *, promotion_index: int) -> SlotCandidate:
    return {
        "slot": promotion["slot"],
        "display_value": promotion["display_value"],
        "normalized_value": promotion["normalized_value"],
        "compact_value": promotion["compact_value"],
        "numeric_value": promotion["numeric_value"],
        "date_value": promotion["date_value"],
        "strategy": "release_promotion",
        "confidence": promotion["confidence"],
        "ambiguity_group": promotion["slot"],
        "is_projection_backed": 1,
        "candidate_layer": "release",
        "candidate_origin": "release_promotion",
        "origin_path": promotion["source_path"],
        "origin_kind": "release_rule",
        "evidence_paths": [promotion["source_path"]],
        "projection_id": promotion["projection_id"],
        "promotion_index": promotion_index,
    }
