from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from semantic_control_kernel.workflows.llm_calls.update_state_builders import (
    UpdateStateBuilderError,
    create_taxonomy_update_state,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "valid_payloads.json"


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_builds_creation_taxonomy_update_state(tmp_path: Path) -> None:
    fixtures = _fixtures()

    taxonomy = create_taxonomy_update_state(
        fixtures["taxonomy_to_sample_analyses"],
        analysis_run_id=str(fixtures["analysis_run_id"]),
        real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        artifact_root=tmp_path,
    )

    assert taxonomy["schema_version"] == "kernel.create_taxonomy_update_state.input.v1"
    assert taxonomy["source_schema_version"] == "kernel.taxonomy_to_sample_analyses.v1"
    assert "taxonomy_id" not in taxonomy["taxonomy_core"]
    assert (tmp_path / "tax_sa" / str(fixtures["analysis_run_id"]) / "tax_update.json").is_file()


def test_creation_taxonomy_builder_rejects_duplicate_codes_and_missing_fallback() -> None:
    fixtures = _fixtures()
    duplicate = deepcopy(fixtures["taxonomy_to_sample_analyses"])
    duplicate["taxonomy_proposal"]["taxonomy_core"]["field_codes"].append(
        deepcopy(duplicate["taxonomy_proposal"]["taxonomy_core"]["field_codes"][0])
    )
    with pytest.raises(UpdateStateBuilderError):
        create_taxonomy_update_state(
            duplicate,
            analysis_run_id=str(fixtures["analysis_run_id"]),
            real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        )

    missing_fallback = deepcopy(fixtures["taxonomy_to_sample_analyses"])
    missing_fallback["taxonomy_proposal"]["taxonomy_core"]["fallback_codes"]["field_code"] = "misc"
    with pytest.raises(UpdateStateBuilderError):
        create_taxonomy_update_state(
            missing_fallback,
            analysis_run_id=str(fixtures["analysis_run_id"]),
            real_taxonomy_proof=fixtures["real_taxonomy_proof"],
        )
