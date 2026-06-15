from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


ADAPTER_CATEGORIES: tuple[str, ...] = (
    "WorkspaceAdapter",
    "OrchestratorAdapter",
    "CorpusAdapter",
    "SemanticReleaseAdapter",
    "PipelineBatchAdapter",
    "MergeAdapter",
    "EmbeddingAdapter",
    "OptimizerAdapter",
    "InterpreterAdapter",
    "ValidatorAdapter",
    "NormalizerAdapter",
    "kernel_internal_no_pipeline_adapter",
)

FALSE_FRIEND_TOOL_NAMES: tuple[str, ...] = (
    "inspect_active_corpus",
    "activation_preflight",
    "semantic_audit",
    "activate_release_on_existing_db",
    "merge_corpora",
    "rebuild_corpus_from_artifacts",
)

INVALID_KERNEL_NAME_CANDIDATES: tuple[str, ...] = (
    "update_semantic_release",
    "attach_custom_projection_to_database",
    "attach_custom_taxonomy_to_database",
    "attach_default_projection_to_database",
    "attach_default_taxonomy_with_projections_to_database",
)

LLM_SUPPLEMENTED_FUNCTIONS: tuple[str, ...] = (
    "analyze_samples",
    "create_taxonomy_to_sample_analyses",
    "create_projections_to_sample_analyses",
)

UPDATE_STATE_BUILDER_FUNCTIONS: tuple[str, ...] = (
    "create_taxonomy_update_state",
    "create_projections_update_state",
)

PIPELINE_ADAPTER_EXCLUDED_FUNCTIONS: tuple[str, ...] = (
    *LLM_SUPPLEMENTED_FUNCTIONS,
    *UPDATE_STATE_BUILDER_FUNCTIONS,
)


@dataclass(frozen=True)
class RequiredPipelineCapability:
    capability_name: str
    status: str
    owner_home: str
    required_for_full_execution: str
    blocking_behavior_until_available: str
    blocked_until: str = "phase_19"
    recovery_state_class: str = "support_only_unrecoverable"
    source_spec_refs: tuple[str, ...] = (
        "SPEC_Semantic_Control_Kernel_Build.md#Phase 4 - Pipeline Adapter Boundary",
    )
    recommended_implementation_target: str = "Phase 19 owner-local contract hardening"


REQUIRED_PIPELINE_CAPABILITIES = MappingProxyType(
    {
        "artifact_tree_contract_hardening": RequiredPipelineCapability(
            capability_name="Artifact Tree Contract Hardening",
            status="implemented_in_pipeline",
            owner_home=(
                "Orchestrator workspace support, Corpus Builder workspace support "
                "or shared workspace-domain package"
            ),
            required_for_full_execution="Phase 9 and Phase 12 owner-backed workflow execution",
            blocked_until="phase_19_completed",
            blocking_behavior_until_available=(
                "Owner-backed happy path is live; incomplete requests fail with blocked_by_kernel_precondition and unproven mutations fail with target_identity_unproven"
            ),
            recommended_implementation_target=(
                "Expose create_artifact_tree and validate_artifact_tree through an owner-local workspace contract"
            ),
        ),
        "semantic_release_domain_service": RequiredPipelineCapability(
            capability_name="Semantic Release Domain Service",
            status="implemented_in_pipeline",
            owner_home=(
                "04 - Normalizer/normalizer_vision/source_authoring/ and "
                "normalizer_vision/semantic_release/ exposed through normalizer_vision.edit_contract"
            ),
            required_for_full_execution="Phase 9, Phase 10 and Phase 12 owner-backed semantic mutation execution",
            blocked_until="phase_19_completed",
            blocking_behavior_until_available=(
                "Owner-backed happy path is live; incomplete requests fail with blocked_by_kernel_precondition and unproven mutations fail with target_identity_unproven"
            ),
            recommended_implementation_target=(
                "Expose semantic release authoring, validation and mutation service through normalizer_vision.edit_contract"
            ),
        ),
        "pipeline_batch_manifest_domain_service": RequiredPipelineCapability(
            capability_name="Pipeline Batch Manifest Domain Service",
            status="implemented_in_pipeline",
            owner_home="batch identity in 00 - Orchestrator/orchestrator/pipeline_batches/",
            required_for_full_execution="manual_pipeline_run owner-backed execution",
            blocked_until="phase_19_completed",
            blocking_behavior_until_available=(
                "Owner-backed happy path is live; incomplete requests fail with blocked_by_kernel_precondition and unproven mutations fail with target_identity_unproven"
            ),
            recommended_implementation_target=(
                "Expose batch manifest create/finalize owner actions"
            ),
        ),
        "multi_source_merge_domain_service": RequiredPipelineCapability(
            capability_name="Multi-Source Merge Domain Service",
            status="implemented_in_pipeline",
            owner_home=(
                "05 - Corpus Builder/corpus_builder/semantic_release/ plus Normalizer semantic merge "
                "via normalizer_vision.edit_contract"
            ),
            required_for_full_execution="Phase 12 owner-backed merge execution",
            blocked_until="phase_19_completed",
            blocking_behavior_until_available=(
                "Owner-backed happy path is live; incomplete requests fail with blocked_by_kernel_precondition"
            ),
            recommended_implementation_target=(
                "Expose multi-source SQL/artifact/semantic merge and reconciliation owner actions"
            ),
        ),
    }
)
