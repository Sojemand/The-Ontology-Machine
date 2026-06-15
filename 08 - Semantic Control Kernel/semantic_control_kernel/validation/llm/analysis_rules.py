from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.policy.promotion_slots import (
    promotion_slot_names,
    promotion_slot_registry_errors,
)
from semantic_control_kernel.validation.llm.common import (
    _ASCII_SNAKE_RE,
    _PROJECTION_ID_RE,
    ValidationError,
    code_list_errors,
    domain_marker_ids,
    find_mapping,
    field_promotion_slot_errors,
    include_key_to_section,
    iter_code_values,
    promotion_slot_errors,
    promotion_source_cell_errors,
    promotion_source_field_errors,
    promotion_source_path_errors,
    subset_errors,
)
from semantic_control_kernel.validation.llm.context import LLMValidationContext
from semantic_control_kernel.validation.llm.taxonomy_value_rules import value_type_errors


def sample_analysis_errors(
    payload: Mapping[str, Any],
    context: LLMValidationContext,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    sample_set = payload.get("sample_set")
    if isinstance(sample_set, Mapping) and context.expected_sample_ids:
        actual = tuple(str(item) for item in sample_set.get("sample_ids", ()))
        if actual != context.expected_sample_ids:
            errors.append(
                (
                    "sample_id_mismatch",
                    f"sample_set.sample_ids must match prompt input order {context.expected_sample_ids}.",
                    "$.sample_set.sample_ids",
                )
            )
    if isinstance(sample_set, Mapping) and not str(sample_set.get("summary", "")).strip():
        errors.append(
            (
                "function_rule_violation",
                "sample_set.summary must contain substantive sample analysis text.",
                "$.sample_set.summary",
            )
        )
    taxonomy_seed = find_mapping(payload, "taxonomy_seed")
    if isinstance(taxonomy_seed, Mapping) and isinstance(taxonomy_seed.get("candidate_codes"), list):
        errors.extend(code_list_errors(taxonomy_seed["candidate_codes"], "$.taxonomy_seed.candidate_codes"))
    projection_seed = find_mapping(payload, "projection_seed")
    if isinstance(projection_seed, Mapping) and isinstance(projection_seed.get("candidate_projection_ids"), list):
        seen_projection_ids: set[str] = set()
        for index, projection_id in enumerate(projection_seed["candidate_projection_ids"]):
            projection_text = str(projection_id)
            if not _PROJECTION_ID_RE.match(projection_text):
                errors.append(
                    (
                        "unknown_projection_id",
                        f"candidate projection_id must be a stable ASCII projection id: {projection_text!r}.",
                        f"$.projection_seed.candidate_projection_ids[{index}]",
                    )
                )
            if projection_text in seen_projection_ids:
                errors.append(
                    (
                        "unknown_projection_id",
                        f"candidate projection_id {projection_text!r} must be unique.",
                        f"$.projection_seed.candidate_projection_ids[{index}]",
                    )
                )
            seen_projection_ids.add(projection_text)
    report_seed = payload.get("user_report_samples_seed")
    if not isinstance(report_seed, Mapping) or not report_seed:
        errors.append(
            (
                "function_rule_violation",
                "user_report_samples_seed must be a grounded non-empty object.",
                "$.user_report_samples_seed",
            )
    )
    return errors


def taxonomy_proposal_errors(payload: Mapping[str, Any]) -> list[ValidationError]:
    proposal = payload.get("taxonomy_proposal")
    if not isinstance(proposal, Mapping):
        return []
    errors: list[ValidationError] = []
    if "taxonomy_id" in proposal:
        errors.append(("function_rule_violation", "taxonomy proposal must not include taxonomy_id.", "$.taxonomy_proposal.taxonomy_id"))
    fallback = find_mapping(proposal, "fallback_codes")
    if fallback and "other" not in set(str(value) for value in fallback.values()):
        errors.append(("function_rule_violation", "taxonomy proposal fallback_codes must include other.", "$.taxonomy_proposal.fallback_codes"))
    core = proposal.get("taxonomy_core")
    if isinstance(core, Mapping):
        promotion_slots = core.get("promotion_slots", [])
        errors.extend(promotion_slot_registry_errors(promotion_slots, path="$.taxonomy_proposal.taxonomy_core.promotion_slots"))
        allowed_slots = promotion_slot_names(promotion_slots)
        errors.extend(field_promotion_slot_errors(proposal, allowed_slots, "$.taxonomy_proposal"))
        errors.extend(value_type_errors(core))
    for path, code in iter_code_values(proposal):
        if code != "other" and not _ASCII_SNAKE_RE.match(code):
            errors.append(("function_rule_violation", f"Taxonomy code {code!r} must be ASCII snake_case.", f"$.taxonomy_proposal{path}"))
    return errors


def projection_proposal_errors(
    payload: Mapping[str, Any],
    context: LLMValidationContext,
) -> list[ValidationError]:
    proposals = payload.get("projection_proposals")
    if not isinstance(proposals, list):
        return []
    errors: list[ValidationError] = []
    seen_ids: set[str] = set()
    for index, proposal in enumerate(proposals):
        if not isinstance(proposal, Mapping):
            continue
        projection_id = str(proposal.get("projection_id", ""))
        if not _PROJECTION_ID_RE.match(projection_id):
            errors.append(("unknown_projection_id", f"Invalid projection_id {projection_id!r}.", f"$.projection_proposals[{index}].projection_id"))
        if projection_id in seen_ids:
            errors.append(("unknown_projection_id", f"Duplicate projection_id {projection_id!r}.", f"$.projection_proposals[{index}].projection_id"))
        seen_ids.add(projection_id)
        domain_ids = proposal.get("domain_ids")
        if isinstance(domain_ids, list):
            errors.extend(
                subset_errors(
                    domain_ids,
                    context.allowed_taxonomy_codes.get("domains", ()),
                    f"$.projection_proposals[{index}].domain_ids",
                )
            )
        for key, value in proposal.items():
            if key.startswith("include_") and isinstance(value, list):
                if "other" not in value:
                    errors.append(("unknown_taxonomy_code", f"{key} must include other fallback.", f"$.projection_proposals[{index}].{key}"))
                errors.extend(
                    subset_errors(
                        value,
                        context.allowed_taxonomy_codes.get(include_key_to_section(key), ()),
                        f"$.projection_proposals[{index}].{key}",
                    )
                )
        routing = proposal.get("routing")
        if isinstance(routing, Mapping) and isinstance(routing.get("example_document_types"), list):
            include_document_types = set(proposal.get("include_document_types", ()))
            for document_type in routing["example_document_types"]:
                if document_type not in include_document_types:
                    errors.append(
                        (
                            "unknown_taxonomy_code",
                            "routing.example_document_types must be a subset of include_document_types.",
                            f"$.projection_proposals[{index}].routing.example_document_types",
                        )
                    )
        lexicon = proposal.get("routing_lexicon")
        if isinstance(lexicon, Mapping):
            allowed_domain_ids = set(str(value) for value in proposal.get("domain_ids", ()) if isinstance(value, str))
            for domain_id in domain_marker_ids(lexicon.get("domain_markers")):
                if allowed_domain_ids and domain_id not in allowed_domain_ids:
                    errors.append(
                        (
                            "unknown_taxonomy_code",
                            "routing_lexicon.domain_markers keys must exist in domain_ids.",
                            f"$.projection_proposals[{index}].routing_lexicon.domain_markers",
                        )
                    )
                    break
        included_fields = tuple(str(item) for item in (proposal.get("include_field_codes") or ()) if isinstance(item, str))
        included_cells = tuple(str(item) for item in (proposal.get("include_cell_codes") or ()) if isinstance(item, str))
        errors.extend(promotion_slot_errors(proposal, context, f"$.projection_proposals[{index}]", require_registry=True))
        errors.extend(promotion_source_path_errors(proposal, f"$.projection_proposals[{index}]"))
        errors.extend(
            promotion_source_field_errors(
                proposal,
                known_field_codes=context.allowed_taxonomy_codes.get("field_codes", ()),
                included_field_codes=included_fields,
                path=f"$.projection_proposals[{index}]",
            )
        )
        errors.extend(
            promotion_source_cell_errors(
                proposal,
                known_cell_codes=context.allowed_taxonomy_codes.get("cell_codes", ()),
                included_cell_codes=included_cells,
                path=f"$.projection_proposals[{index}]",
            )
        )
    return errors
