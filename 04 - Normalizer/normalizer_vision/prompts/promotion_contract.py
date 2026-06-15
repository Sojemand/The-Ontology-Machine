from __future__ import annotations

from typing import Any

from ..taxonomy import TaxonomyProfile


def promotion_contract_lines(profile: TaxonomyProfile) -> list[str]:
    contract = format_promotion_contract(profile)
    if not contract:
        return []
    lines = [
        "Promotion materialization contract:",
        *contract,
        "",
        "Promotion field rules:",
        "- Fields listed above are materialization inputs for the Corpus Builder.",
        "- When input support exists, fill promotion-backed content.fields explicitly.",
        "- For cardinality=multi, return a JSON array of separate values, never a comma-separated string.",
        "- Row cells may reference promoted values, but row cells do not replace promotion-backed content.fields.",
    ]
    if "description" not in profile.cell_codes:
        lines.append("- `description` is not an allowed cell_code for this profile; do not emit row.description.")
    else:
        lines.append("- Use only allowed cell_codes in rows.")
    return lines


def format_promotion_contract(profile: TaxonomyProfile) -> list[str]:
    slot_defs = promotion_slot_defs(profile)
    lines: list[str] = []
    for rule in profile.promotion_rules:
        if not isinstance(rule, dict):
            continue
        slot = str(rule.get("slot") or "").strip()
        if not slot:
            continue
        slot_def = slot_defs.get(slot, {})
        cardinality = str(slot_def.get("cardinality") or "single")
        value_type = str(slot_def.get("value_type") or "string")
        query_role = str(slot_def.get("query_role") or "").strip()
        role_text = f" | query_role={query_role}" if query_role else ""
        for source_path in rule.get("source_paths", []) or []:
            path = str(source_path or "").strip()
            if path:
                lines.append(f"- {path} -> {slot} | cardinality={cardinality} | value_type={value_type}{role_text}")
    return lines


def promotion_field_specs(profile: TaxonomyProfile) -> dict[str, dict[str, str]]:
    slot_defs = promotion_slot_defs(profile)
    specs: dict[str, dict[str, str]] = {}
    for rule in profile.promotion_rules:
        if not isinstance(rule, dict):
            continue
        slot_def = slot_defs.get(str(rule.get("slot") or "").strip(), {})
        cardinality = str(slot_def.get("cardinality") or "single")
        value_type = str(slot_def.get("value_type") or "string")
        for source_path in rule.get("source_paths", []) or []:
            field_code = field_code_from_source_path(str(source_path or ""))
            if field_code and (field_code not in specs or specs[field_code]["cardinality"] != "multi"):
                specs[field_code] = {"cardinality": cardinality, "value_type": value_type}
    return specs


def promotion_slot_defs(profile: TaxonomyProfile) -> dict[str, dict[str, Any]]:
    return {
        str(slot_def.get("slot") or "").strip(): slot_def
        for slot_def in profile.promotion_slots
        if isinstance(slot_def, dict) and str(slot_def.get("slot") or "").strip()
    }


def field_code_from_source_path(source_path: str) -> str | None:
    prefix = "content.fields."
    if not source_path.startswith(prefix):
        return None
    tail = source_path[len(prefix) :]
    field_code = tail.split(".", 1)[0].split("[", 1)[0].strip()
    return field_code or None
