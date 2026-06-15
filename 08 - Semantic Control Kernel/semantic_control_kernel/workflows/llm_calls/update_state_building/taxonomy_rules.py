from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.workflows.llm_calls.update_state_building.errors import UpdateStateBuilderError

def _reject_duplicate_codes_by_section(taxonomy_core: Mapping[str, Any]) -> None:
    for section in ("domains", "document_types", "categories", "subcategories", "field_codes", "row_types", "cell_codes"):
        values = taxonomy_core.get(section, [])
        if not isinstance(values, list):
            continue
        seen: set[str] = set()
        for item in values:
            if not isinstance(item, Mapping) or not isinstance(item.get("code"), str):
                continue
            code = item["code"]
            if code in seen:
                raise UpdateStateBuilderError(f"duplicate taxonomy code {code!r} in {section}.")
            seen.add(code)
