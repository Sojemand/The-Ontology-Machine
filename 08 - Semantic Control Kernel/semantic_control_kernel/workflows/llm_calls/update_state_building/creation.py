from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.workflows.llm_calls.update_state_building.common import (
    _finalize_update_state,
    _list,
    _mapping,
    _promote_projection,
    _reject_duplicate_codes_by_section,
    _require_validated_source,
    _runtime_locale,
    _semantic_binding_from_proposal,
    _source_artifacts,
    _taxonomy_core_from_proposal,
    _taxonomy_text_from_proposal,
    _validate_projection_precursors,
    _validate_ref_against_proof,
    _validation_stamp,
)
from semantic_control_kernel.workflows.llm_calls.update_state_building.errors import UpdateStateBuilderError

def create_taxonomy_update_state(
    proposal: Mapping[str, Any],
    *,
    analysis_run_id: str,
    artifact_root: str | Path | None = None,
    real_taxonomy_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _require_validated_source("create_taxonomy_to_sample_analyses", proposal)
    taxonomy_proposal = _mapping(proposal, "taxonomy_proposal")
    taxonomy_core = taxonomy_proposal.get("taxonomy_core", taxonomy_proposal)
    if not isinstance(taxonomy_core, Mapping):
        raise UpdateStateBuilderError("taxonomy_core is required.")
    fallback = _mapping(taxonomy_core, "fallback_codes")
    if "other" not in set(str(value) for value in fallback.values()):
        raise UpdateStateBuilderError("taxonomy creation requires fallback code other.")
    _reject_duplicate_codes_by_section(taxonomy_core)
    state = {
        "schema_version": "kernel.create_taxonomy_update_state.input.v1",
        "source_schema_version": "kernel.taxonomy_to_sample_analyses.v1",
        "analysis_scope": "sample_set",
        "analysis_run_id": analysis_run_id,
        "sample_ids": list(proposal.get("sample_ids", [])),
        "source_artifacts": _source_artifacts("tax_sa", analysis_run_id, "tax_sa.json"),
        "taxonomy_identity": {
            "taxonomy_id_policy": "kernel_assigned",
            "runtime_locale": _runtime_locale(real_taxonomy_proof),
        },
        "taxonomy_core": _taxonomy_core_from_proposal(taxonomy_proposal),
        "taxonomy_text": _taxonomy_text_from_proposal(taxonomy_proposal, _runtime_locale(real_taxonomy_proof)),
        "semantic_binding": _semantic_binding_from_proposal(taxonomy_proposal),
        "kernel_policy": {
            "defaults_profile": "custom_taxonomy.v1",
            "governance_profile": "kernel_default",
            "compatibility_profile": "normalizer_current",
        },
        "validation_stamp": _validation_stamp(),
    }
    return _finalize_update_state(state, artifact_root, "tax_sa", analysis_run_id, "tax_update.json")


def create_projections_update_state(
    proposal: Mapping[str, Any],
    *,
    analysis_run_id: str,
    real_taxonomy_proof: Mapping[str, Any],
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    _require_validated_source("create_projections_to_sample_analyses", proposal)
    if not real_taxonomy_proof:
        raise UpdateStateBuilderError("create_projections_update_state requires real taxonomy proof.")
    _validate_ref_against_proof(
        proposal.get("taxonomy_ref"),
        real_taxonomy_proof,
        keys=("taxonomy_id", "taxonomy_version", "taxonomy_fingerprint"),
        label="taxonomy_ref",
    )
    projections = _list(proposal, "projection_proposals")
    _validate_projection_precursors(projections, real_taxonomy_proof)
    state = {
        "schema_version": "kernel.create_projections_update_state.input.v1",
        "source_schema_version": "kernel.projections_to_sample_analyses.v1",
        "taxonomy_view_schema_version": "kernel.taxonomy_projection_authoring_view.v1",
        "analysis_scope": "sample_set",
        "analysis_run_id": analysis_run_id,
        "sample_ids": list(proposal.get("sample_ids", [])),
        "source_artifacts": _source_artifacts("proj_sa", analysis_run_id, "proj_sa.json", view="tax_view.json"),
        "taxonomy_ref": deepcopy(dict(proposal.get("taxonomy_ref", {}))),
        "projection_precursors": [_promote_projection(projection) for projection in projections],
        "validation_stamp": _validation_stamp(),
    }
    return _finalize_update_state(state, artifact_root, "proj_sa", analysis_run_id, "proj_update.json")
