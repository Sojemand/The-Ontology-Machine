from __future__ import annotations

from typing import Any

from . import policy


def validate_semantic_bindings(master_core: dict[str, Any], indexes: dict[str, set[str]]) -> None:
    for section_name, bool_key in (("field_codes", None), ("row_types", "materialize_each_row"), ("cell_codes", "materialize_on_row_entity")):
        for item_key, entry in master_core[section_name].items():
            binding = policy.require_mapping(
                entry.get("semantic_binding"),
                label=f"master.core.{section_name}.{item_key}.semantic_binding",
            )
            if section_name != "cell_codes":
                entity_type = policy.require_text(
                    binding.get("entity_type"),
                    label=f"master.core.{section_name}.{item_key}.semantic_binding.entity_type",
                )
                if entity_type not in indexes["entity_types"]:
                    raise ValueError(f"master.core.{section_name}.{item_key}.semantic_binding.entity_type ist ungueltig: {entity_type}")
            role_type = str(binding.get("role_type") or "").strip()
            if section_name == "field_codes" and role_type and role_type not in indexes["role_types"]:
                raise ValueError(f"master.core.{section_name}.{item_key}.semantic_binding.role_type ist ungueltig: {role_type}")
            if section_name != "row_types":
                policy.require_text(
                    binding.get("attribute_code"),
                    label=f"master.core.{section_name}.{item_key}.semantic_binding.attribute_code",
                )
            legacy_slot_key = "header" + "_slot"
            if legacy_slot_key in binding:
                raise ValueError(f"master.core.{section_name}.{item_key}.semantic_binding enthaelt einen entfernten Promotion-Alias.")
            if bool_key is not None and not isinstance(binding.get(bool_key), bool):
                raise ValueError(f"master.core.{section_name}.{item_key}.semantic_binding.{bool_key} muss bool sein.")
