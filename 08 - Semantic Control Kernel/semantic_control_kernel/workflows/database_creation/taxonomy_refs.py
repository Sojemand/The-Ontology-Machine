from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.database_creation import StagedSemanticReleaseComponent


TAXONOMY_CODE_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
)


def staged_component_from_adapter_output(
    *,
    component_kind: str,
    output: Mapping[str, Any],
    fallback_stage_id: str,
    source_analysis_refs: Sequence[Mapping[str, Any]] = (),
) -> StagedSemanticReleaseComponent:
    component_identity = output.get("component_identity")
    if not isinstance(component_identity, Mapping):
        identity_key = "taxonomy_id" if component_kind == "taxonomy" else "projection_ids"
        component_identity = {identity_key: output.get(identity_key, fallback_stage_id)}
    fingerprint = str(output.get("fingerprint") or output.get("taxonomy_fingerprint") or output.get("projection_set_fingerprint") or stable_hash(str(component_identity)))
    artifact_ref = output.get("artifact_ref") if isinstance(output.get("artifact_ref"), Mapping) else {"artifact_path": output.get("artifact_path", "")}
    return StagedSemanticReleaseComponent(
        component_kind=component_kind,
        stage_id=str(output.get("stage_id", fallback_stage_id)),
        artifact_ref=artifact_ref,
        component_identity=component_identity,
        fingerprint=fingerprint,
        source_analysis_refs=tuple(dict(item) for item in source_analysis_refs),
        validation_status=str(output.get("validation_status", "validated")),
    )


def taxonomy_ref_from_staged_component(
    staged_component_ref: Mapping[str, Any],
    *,
    fallback_update_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    component_identity = staged_component_ref.get("component_identity")
    if not isinstance(component_identity, Mapping):
        return {}
    update_state = fallback_update_state
    if not isinstance(update_state, Mapping):
        update_state = _first_taxonomy_update_state(staged_component_ref)
    return enriched_taxonomy_ref(component_identity, update_state=update_state, source="staged")


def enriched_taxonomy_ref(
    component_identity: Mapping[str, Any],
    *,
    update_state: Mapping[str, Any] | None = None,
    source: str = "active",
) -> dict[str, Any]:
    taxonomy_ref = deepcopy(dict(component_identity))
    if isinstance(update_state, Mapping):
        _merge_taxonomy_update_state(taxonomy_ref, update_state)
    taxonomy_ref.setdefault("source", source)
    return taxonomy_ref


def _first_taxonomy_update_state(staged_component_ref: Mapping[str, Any]) -> Mapping[str, Any] | None:
    refs = staged_component_ref.get("source_analysis_refs")
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        return None
    for ref in refs:
        if isinstance(ref, Mapping) and isinstance(ref.get("taxonomy_core"), Mapping):
            return ref
    return None


def _merge_taxonomy_update_state(taxonomy_ref: dict[str, Any], update_state: Mapping[str, Any]) -> None:
    for key in (
        "schema_version", "source_schema_version", "analysis_scope", "analysis_run_id",
        "sample_ids", "source_artifacts", "taxonomy_identity", "taxonomy_core",
        "taxonomy_text", "semantic_binding", "kernel_policy", "validation_stamp",
    ):
        if key in update_state and key not in taxonomy_ref:
            taxonomy_ref[key] = deepcopy(update_state[key])
    core = update_state.get("taxonomy_core")
    if not isinstance(core, Mapping):
        return
    for section in TAXONOMY_CODE_SECTIONS:
        values = core.get(section)
        if isinstance(values, list) and section not in taxonomy_ref:
            taxonomy_ref[section] = deepcopy(values)
    fallback_codes = core.get("fallback_codes")
    if isinstance(fallback_codes, Mapping) and "fallback_codes" not in taxonomy_ref:
        taxonomy_ref["fallback_codes"] = sorted(str(value) for value in fallback_codes.values() if str(value))
        taxonomy_ref["fallback_code_map"] = deepcopy(dict(fallback_codes))
    promotion_slots = core.get("promotion_slots")
    if isinstance(promotion_slots, list) and "promotion_slots" not in taxonomy_ref:
        taxonomy_ref["promotion_slots"] = deepcopy(promotion_slots)
