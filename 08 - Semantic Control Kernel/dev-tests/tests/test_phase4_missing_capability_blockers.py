from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.adapter_results import AdapterCallResult


def _assert_precondition_blocker(result: AdapterCallResult) -> None:
    payload = result.to_dict()

    assert payload["schema_version"] == "adapter.call_result.v1"
    assert payload["status"] == "blocked_by_kernel_precondition"
    assert payload["capability_status"] == "implemented_in_pipeline"
    assert payload["diagnostics"][0]["code"] == "blocked_by_kernel_precondition"
    assert payload["diagnostics"][0]["missing_fields"]


def test_supported_owner_backed_capabilities_fail_closed_with_precondition_blockers_when_request_context_is_missing(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    cases = (
        WorkspaceAdapter(state_root=state_root).prepare_artifact_tree({}),
        CorpusAdapter(state_root=state_root).create_empty_database({}),
        SemanticReleaseAdapter(state_root=state_root).stage_taxonomy({}),
        PipelineBatchAdapter(state_root=state_root).create_batch_manifest({}),
        MergeAdapter(state_root=state_root).multi_source_merge_preflight({}),
    )

    for result in cases:
        _assert_precondition_blocker(result)


def test_precondition_blockers_do_not_invoke_or_persist_owner_calls(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    result = WorkspaceAdapter(state_root=state_root).validate_artifact_tree({})

    assert result.to_dict()["status"] == "blocked_by_kernel_precondition"
    adapter_calls_dir = StatePaths.from_state_root(state_root).adapter_calls_dir
    assert adapter_calls_dir.exists()
    assert not any(adapter_calls_dir.iterdir())
