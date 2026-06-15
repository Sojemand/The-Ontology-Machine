from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from semantic_control_kernel.types.llm_calls import LLMFunctionDefinition
from semantic_control_kernel.policy.promotion_slots import promotion_slot_names
from semantic_control_kernel.validation.llm.common import (
    find_first_list,
    find_mapping,
    first_mapping_at_keys,
    iter_key_values,
    unique,
)


@dataclass(frozen=True)
class LLMValidationContext:
    expected_sample_ids: tuple[str, ...] = ()
    expected_database_ref: Mapping[str, Any] | None = None
    expected_taxonomy_ref: Mapping[str, Any] | None = None
    expected_semantic_release_ref: Mapping[str, Any] | None = None
    expected_projection_ids: tuple[str, ...] = ()
    allowed_update_modes: tuple[str, ...] = ()
    allowed_taxonomy_codes: Mapping[str, Sequence[str]] = field(default_factory=dict)
    allowed_taxonomy_code_set: tuple[str, ...] = ()
    fallback_taxonomy_code_set: tuple[str, ...] = ()
    allowed_promotion_slots: tuple[str, ...] = ()
    allowed_action_ids: tuple[str, ...] = ()
    input_payload: Any = None


def derive_validation_context(definition: LLMFunctionDefinition, input_payload: Any) -> LLMValidationContext:
    sample_ids = _sample_ids_from_input(input_payload)
    database_ref = first_mapping_at_keys(input_payload, ("database_ref",))
    taxonomy_ref = first_mapping_at_keys(input_payload, ("taxonomy_ref",))
    semantic_release_ref = first_mapping_at_keys(input_payload, ("semantic_release_ref", "semantic_release"))
    allowed_modes = _allowed_update_modes(input_payload)
    allowed_codes = _allowed_codes(input_payload)
    allowed_code_set = _allowed_code_set(input_payload)
    fallback_code_set = _fallback_code_set(input_payload)
    promotion_slots = _promotion_slots(input_payload)
    projection_ids = tuple(_projection_ids(input_payload))
    return LLMValidationContext(
        expected_sample_ids=tuple(sample_ids),
        expected_database_ref=database_ref,
        expected_taxonomy_ref=taxonomy_ref,
        expected_semantic_release_ref=semantic_release_ref,
        expected_projection_ids=projection_ids,
        allowed_update_modes=tuple(allowed_modes),
        allowed_taxonomy_codes=allowed_codes,
        allowed_taxonomy_code_set=tuple(allowed_code_set),
        fallback_taxonomy_code_set=tuple(fallback_code_set),
        allowed_promotion_slots=tuple(promotion_slots),
        input_payload=deepcopy(input_payload),
    )


def _allowed_update_modes(value: Any) -> list[str]:
    mapping = find_mapping(value, "update_policy")
    modes = mapping.get("allowed_update_modes") if mapping else None
    if isinstance(modes, list):
        return [str(mode) for mode in modes]
    return []


def _allowed_codes(value: Any) -> dict[str, Sequence[str]]:
    mapping = find_mapping(value, "allowed_codes")
    if not isinstance(mapping, Mapping):
        return {}
    return {str(key): tuple(str(item) for item in child) for key, child in mapping.items() if isinstance(child, list)}


def _allowed_code_set(value: Any) -> list[str]:
    mapping = find_mapping(value, "allowed_codes")
    if isinstance(mapping, Mapping):
        codes: list[str] = []
        for child in mapping.values():
            if isinstance(child, list):
                codes.extend(str(item) for item in child)
        return list(unique(codes))
    if isinstance(mapping, list):
        return [str(item) for item in mapping]
    boundary = find_mapping(value, "taxonomy_boundary")
    if isinstance(boundary, Mapping) and isinstance(boundary.get("allowed_codes"), list):
        return [str(item) for item in boundary["allowed_codes"]]
    return []


def _fallback_code_set(value: Any) -> list[str]:
    mapping = find_mapping(value, "fallback_codes")
    codes: list[str] = []
    if isinstance(mapping, Mapping):
        for child in mapping.values():
            if isinstance(child, list):
                codes.extend(str(item) for item in child)
            elif isinstance(child, str):
                codes.append(child)
    boundary = find_mapping(value, "taxonomy_boundary")
    if isinstance(boundary, Mapping):
        fallback = boundary.get("fallback_codes")
        if isinstance(fallback, Mapping):
            for child in fallback.values():
                if isinstance(child, list):
                    codes.extend(str(item) for item in child)
                elif isinstance(child, str):
                    codes.append(child)
        elif isinstance(fallback, list):
            codes.extend(str(item) for item in fallback)
    return list(unique(codes))


def _promotion_slots(value: Any) -> list[str]:
    slots = find_first_list(value, "promotion_slots")
    if not isinstance(slots, list):
        return []
    return promotion_slot_names(slots)


def _sample_ids_from_input(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item["sample_id"]) for item in value if isinstance(item, Mapping) and "sample_id" in item]
    if isinstance(value, Mapping):
        if isinstance(value.get("sample_ids"), list):
            return [str(item) for item in value["sample_ids"]]
        sample_analyses = value.get("sample_analyses")
        if isinstance(sample_analyses, Mapping):
            return _sample_ids_from_input(sample_analyses)
    return []


def _projection_ids(value: Any) -> list[str]:
    ids: list[str] = []
    index = find_mapping(value, "projection_index")
    if index and isinstance(index.get("projection_ids"), list):
        ids.extend(str(item) for item in index["projection_ids"])
    for _path, projection_id in iter_key_values(value, "projection_id"):
        ids.append(str(projection_id))
    return list(unique(ids))
