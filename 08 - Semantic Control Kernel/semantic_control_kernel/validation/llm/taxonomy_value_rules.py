from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.promotion_slots import promotion_value_types
from semantic_control_kernel.validation.llm.common import ValidationError


def value_type_errors(core: Mapping[str, Any]) -> list[ValidationError]:
    allowed = set(promotion_value_types())
    errors: list[ValidationError] = []
    for section in ("field_codes", "cell_codes"):
        values = core.get(section, [])
        if not isinstance(values, list):
            continue
        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                continue
            value_type = str(item.get("value_type") or "")
            if value_type not in allowed:
                errors.append(("enum_mismatch", f"{section} value_type {value_type!r} is not supported.", f"$.taxonomy_proposal.taxonomy_core.{section}[{index}].value_type"))
    return errors
