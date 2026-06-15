from __future__ import annotations

from pathlib import Path

import pytest

from _phase9_fakes import (
    FakeLLMPort,
    FakeSemanticReleaseAdapter,
    load_default_release_fixture,
    runtime_for,
    sample_refs_for,
    target_for,
)
from phase9_creation_route_expectations import FROZEN_CREATION_GOLDEN
from phase9_creation_route_observation import canonical_artifact_folders, freeze_observation
from semantic_control_kernel.types.database_creation import CANONICAL_ARTIFACT_FOLDERS
from semantic_control_kernel.workflows.database_creation.route_sequences import route_sequence
from semantic_control_kernel.workflows.database_creation.routes import run_database_creation_workflow


@pytest.mark.parametrize(
    "golden",
    FROZEN_CREATION_GOLDEN["workflows"],
    ids=[entry["workflow_tool"] for entry in FROZEN_CREATION_GOLDEN["workflows"]],
)
def test_frozen_primary_creation_workflows_match_golden_e2e_artifacts(tmp_path: Path, golden: dict[str, object]) -> None:
    workflow_tool = str(golden["workflow_tool"])
    target_payload = golden["target"]
    assert isinstance(target_payload, dict)
    target = target_for(
        tmp_path,
        name=str(target_payload["artifact_root_name"]),
        database_name=str(target_payload["database_name"]),
    )
    semantic = FakeSemanticReleaseAdapter()
    llm = FakeLLMPort()
    runtime_kwargs = {"target": target, "semantic_adapter": semantic}
    if "custom_taxonomy" in workflow_tool:
        runtime_kwargs["llm_port"] = llm
        runtime_kwargs["taxonomy_samples"] = sample_refs_for(target, prefix="taxonomy")
    if "custom_projections" in workflow_tool:
        runtime_kwargs["llm_port"] = llm
        runtime_kwargs["projection_samples"] = sample_refs_for(target, prefix="projection")
    if workflow_tool == "empty_database_default_taxonomy_custom_projections":
        runtime_kwargs["taxonomy_ref"] = load_default_release_fixture()["taxonomy_ref"]

    execution = run_database_creation_workflow(
        workflow_tool,
        runtime=runtime_for(tmp_path, **runtime_kwargs),
        workflow_run_id=str(golden["workflow_run_id"]),
    )

    assert freeze_observation(execution, semantic, llm, target, tmp_path) == golden
    assert route_sequence(workflow_tool) == tuple(golden["completed_step_ids"])
    assert Path(target.database_path).is_file()
    assert canonical_artifact_folders(target) == CANONICAL_ARTIFACT_FOLDERS
    assert execution.mirror_events[-1]["event_type"] == "workflow_completed"
    assert execution.mirror_events[-1]["technical_detail_ref"]["workflow_completion"]["workflow_tool"] == workflow_tool
