from __future__ import annotations

from semantic_control_kernel.adapters.capabilities import PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS
from semantic_control_kernel.adapters.registry import AdapterRegistry, CANONICAL_FUNCTION_ADAPTER_MAP
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter


def test_selected_canonical_functions_map_to_expected_adapters() -> None:
    assert CANONICAL_FUNCTION_ADAPTER_MAP["create_empty_database"].categories == ("CorpusAdapter",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["create_empty_database"].methods == ("create_empty_database",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["activate_semantic_release"].categories == ("SemanticReleaseAdapter",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["create_custom_taxonomy"].methods == ("create_custom_taxonomy",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["create_custom_projection"].methods == ("create_custom_projection",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["stage_custom_taxonomy_for_semantic_release"].methods == ("stage_taxonomy",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["stage_custom_projections_for_semantic_release"].methods == ("stage_projections",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["pipeline_run"].categories == (
        "OrchestratorAdapter",
        "CorpusAdapter",
        "PipelineBatchAdapter",
    )
    assert CANONICAL_FUNCTION_ADAPTER_MAP["database_merge_additive_only"].categories == ("MergeAdapter",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["database_rebuild_from_artifacts"].categories == (
        "WorkspaceAdapter",
        "CorpusAdapter",
        "SemanticReleaseAdapter",
        "EmbeddingAdapter",
    )
    assert CANONICAL_FUNCTION_ADAPTER_MAP["kernel_status"].categories == ("kernel_internal_no_pipeline_adapter",)


def test_phase19_completed_capabilities_no_longer_advertise_deferred_status_in_phase4_mapping() -> None:
    assert CANONICAL_FUNCTION_ADAPTER_MAP["create_standard_artifact_folder_tree"].capability_status == ("implemented_in_pipeline",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["stage_custom_taxonomy_for_semantic_release"].capability_status == ("implemented_in_pipeline",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["pipeline_run"].capability_status == ("implemented_in_pipeline",)
    assert CANONICAL_FUNCTION_ADAPTER_MAP["database_merge_additive_only"].capability_status == ("implemented_in_pipeline",)


def test_semantic_release_adapter_uses_new_method_names_only() -> None:
    expected = {
        "write_semantic_release",
        "load_semantic_release",
        "preflight_semantic_release_activation",
        "activate_semantic_release",
        "create_custom_semantic_release",
    }
    forbidden = {
        "publish_release",
        "load_release",
        "activation_preflight",
        "activate_release",
        "create_custom_release",
    }

    for name in expected:
        assert hasattr(SemanticReleaseAdapter, name)
    for name in forbidden:
        assert not hasattr(SemanticReleaseAdapter, name)


def test_workflow_starters_map_to_kernel_internal_no_pipeline_adapter() -> None:
    starters = (
        "empty_database_no_semantic_release",
        "empty_database_default_taxonomy_no_projections",
        "empty_database_default_taxonomy_default_projections",
        "empty_database_default_taxonomy_custom_projections",
        "empty_database_custom_taxonomy_no_projections",
        "empty_database_custom_taxonomy_custom_projections",
        "manual_pipeline_run",
        "create_custom_taxonomy_path",
        "create_custom_projection_path",
    )
    for name in starters:
        assert CANONICAL_FUNCTION_ADAPTER_MAP[name].categories == ("kernel_internal_no_pipeline_adapter",)
        assert not AdapterRegistry.is_pipeline_adapter_dispatchable(name)


def test_llm_interaction_and_update_state_builders_are_excluded_from_pipeline_adapters() -> None:
    for name in PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS:
        assert name not in CANONICAL_FUNCTION_ADAPTER_MAP
        assert not AdapterRegistry.is_pipeline_adapter_dispatchable(name)
