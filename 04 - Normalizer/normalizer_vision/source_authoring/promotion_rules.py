"""Dynamic Promotion Slot helpers for custom source materialization."""
from __future__ import annotations

from typing import Any

from ..taxonomy.promotion_rules import clone_promotion_slots, field_slot_map, promotion_rules_from_fields


def promotion_slots_from_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, field in enumerate(fields):
        slot = str(field.get("promotion_slot") or "").strip()
        if not slot or slot in seen:
            continue
        slots.append(
            {
                "slot": slot,
                "value_type": str(field.get("value_type") or "string"),
                "scope": "document",
                "cardinality": str(field.get("promotion_cardinality") or field.get("cardinality") or "single"),
                "query_role": field.get("query_role") or ("primary" if not slots else "secondary"),
                "display_rank": int(field.get("display_rank") or ((index + 1) * 10)),
            }
        )
        seen.add(slot)
    return slots
