from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from semantic_control_kernel.workflows.llm_calls.update_state_builders import (
    UpdateStateBuilderError,
    create_projections_update_state,
)
from semantic_control_kernel.workflows.llm_calls.update_state_building.operations import _promote_projection


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_builds_creation_projection_update_state(tmp_path: Path) -> None:
    fixtures = _fixtures()

    creation = create_projections_update_state(
        fixtures["projections_to_sample_analyses"],
        analysis_run_id=str(fixtures["analysis_run_id"]),
        real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        artifact_root=tmp_path,
    )

    assert creation["schema_version"] == "kernel.create_projections_update_state.input.v1"
    assert creation["source_schema_version"] == "kernel.projections_to_sample_analyses.v1"
    assert creation["projection_precursors"][0]["status"] == "active"
    assert (tmp_path / "proj_sa" / str(fixtures["analysis_run_id"]) / "proj_update.json").is_file()


def test_projection_promotion_normalizer_drops_unmapped_rules() -> None:
    fixtures = _fixtures()
    proposal = deepcopy(fixtures["projections_to_sample_analyses"])
    proposal["projection_proposals"][0]["promotion_rules"].append(
        {"slot": "amount_due", "source_paths": []}
    )

    promoted = _promote_projection(proposal["projection_proposals"][0])

    rules = promoted["promotion_rules"]
    assert [rule["slot"] for rule in rules] == ["counterparty"]
    assert all(rule["source_paths"] for rule in rules)


def test_creation_projection_builder_rejects_unknown_codes_invalid_ids_and_stale_taxonomy() -> None:
    fixtures = _fixtures()
    unknown_code = deepcopy(fixtures["projections_to_sample_analyses"])
    unknown_code["projection_proposals"][0]["include_document_types"] = ["unknown_code", "other"]
    with pytest.raises(UpdateStateBuilderError):
        create_projections_update_state(
            unknown_code,
            analysis_run_id=str(fixtures["analysis_run_id"]),
            real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        )

    invalid_id = deepcopy(fixtures["projections_to_sample_analyses"])
    invalid_id["projection_proposals"][0]["projection_id"] = "Bad Projection"
    with pytest.raises(UpdateStateBuilderError):
        create_projections_update_state(
            invalid_id,
            analysis_run_id=str(fixtures["analysis_run_id"]),
            real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        )

    stale_taxonomy = deepcopy(fixtures["projections_to_sample_analyses"])
    stale_taxonomy["taxonomy_ref"]["taxonomy_fingerprint"] = "sha256:stale"
    with pytest.raises(UpdateStateBuilderError):
        create_projections_update_state(
            stale_taxonomy,
            analysis_run_id=str(fixtures["analysis_run_id"]),
            real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        )
