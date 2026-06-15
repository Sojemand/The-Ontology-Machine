from __future__ import annotations

from types import MappingProxyType

from semantic_control_kernel.adapters.registry_types import KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, mapping as _m


CANONICAL_FUNCTION_ADAPTER_MAP = MappingProxyType(
    {
        "create_standard_artifact_folder_tree": _m("WorkspaceAdapter", "prepare_artifact_tree", "implemented_in_pipeline"),
        "create_empty_database": _m("CorpusAdapter", "create_empty_database", "implemented_in_pipeline"),
        "store_active_artifact_folder_tree": _m("WorkspaceAdapter", "validate_artifact_tree", "kernel_composition_over_existing_primitives"),
        "reset_database": _m(("CorpusAdapter", "SemanticReleaseAdapter", "WorkspaceAdapter"), "reset composition", "kernel_composition_over_existing_primitives"),
        "write_semantic_release": _m("SemanticReleaseAdapter", "write_semantic_release", "kernel_composition_over_existing_primitives"),
        "attach_semantic_release_to_database": _m(("SemanticReleaseAdapter", "CorpusAdapter"), "Kernel attach state plus owner load/preflight evidence", "kernel_composition_over_existing_primitives"),
        "attach_default_semantic_release_to_database": _m(("SemanticReleaseAdapter", "CorpusAdapter"), "default release export/load plus attach composition", "kernel_composition_over_existing_primitives"),
        "attach_custom_semantic_release_to_database": _m(("SemanticReleaseAdapter", "CorpusAdapter"), "custom release load plus attach composition", "kernel_composition_over_existing_primitives"),
        "activate_semantic_release": _m("SemanticReleaseAdapter", ("preflight_semantic_release_activation", "activate_semantic_release"), "implemented_in_pipeline"),
        "stage_custom_taxonomy_for_semantic_release": _m("SemanticReleaseAdapter", "stage_taxonomy", "implemented_in_pipeline"),
        "stage_custom_projections_for_semantic_release": _m("SemanticReleaseAdapter", "stage_projections", "implemented_in_pipeline"),
        "create_custom_semantic_release": _m("SemanticReleaseAdapter", "create_custom_semantic_release", "implemented_in_pipeline"),
        "create_custom_taxonomy": _m("SemanticReleaseAdapter", "create_custom_taxonomy", "implemented_in_pipeline"),
        "create_custom_projection": _m("SemanticReleaseAdapter", "create_custom_projection", "implemented_in_pipeline"),
        "validate_projections_against_taxonomy": _m("SemanticReleaseAdapter", "validate_projection_binding", "implemented_in_pipeline"),
        "pipeline_run": _m(("OrchestratorAdapter", "CorpusAdapter", "PipelineBatchAdapter"), ("OrchestratorAdapter.run_pipeline", "PipelineBatchAdapter.create_batch_manifest", "PipelineBatchAdapter.finalize_batch_manifest"), "implemented_in_pipeline"),
        "database_merge_additive_only": _m("MergeAdapter", "multi_source_merge_preflight", "implemented_in_pipeline"),
        "empty_databases_merge_path": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow route composed from merge functions", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "filled_databases_merge_path": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow route composed from merge functions", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "merge_database_empty": _m("MergeAdapter", "merge_empty_databases", "implemented_in_pipeline"),
        "merge_database_filled_additive": _m("MergeAdapter", "merge_filled_databases", "implemented_in_pipeline"),
        "merge_taxonomy_and_projections_additive": _m(("MergeAdapter", "SemanticReleaseAdapter"), "merge_semantic_release_candidates", "implemented_in_pipeline"),
        "reconcile_merged_semantic_release": _m(("MergeAdapter", "SemanticReleaseAdapter"), "write_merge_reconciliation_manifest plus semantic validation", "implemented_in_pipeline"),
        "reconcile_merged_database": _m(("MergeAdapter", "CorpusAdapter", "SemanticReleaseAdapter"), "write_merge_reconciliation_manifest plus database write plan validation", "implemented_in_pipeline"),
        "write_combined_database": _m("MergeAdapter", "write_combined_database", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "fill_artifact_folder_tree": _m("MergeAdapter", "fill_artifact_tree", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "backfill_sql": _m("CorpusAdapter", "backfill_sql", "implemented_in_pipeline"),
        "database_rebuild_from_artifacts": _m(("WorkspaceAdapter", "CorpusAdapter", "SemanticReleaseAdapter", "EmbeddingAdapter"), "rebuild composition", "kernel_composition_over_existing_primitives"),
        "corpus_builder_load_semantic_release": _m(("SemanticReleaseAdapter", "CorpusAdapter"), "load_semantic_release", "implemented_in_pipeline"),
        "run_corpus_builder": _m("CorpusAdapter", "rebuild_from_artifacts", "implemented_in_pipeline"),
        "create_embeddings": _m("EmbeddingAdapter", "create_embeddings", "implemented_in_pipeline"),
        "basic_relation_mining": _m("CorpusAdapter", "basic_relation_mining", "implemented_in_pipeline"),
        "ontology_patch_validation": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "ontology patch validation", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_status": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "Kernel state/repository read", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_resume_state": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "WorkflowResumeStore read", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_continue_resumable_workflow": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "ResumeOptionService plus workflow route continuation", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_cancel_active_run": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "Kernel workflow cancellation", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_apply_recovery_option": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "RecoveryOptionService", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_open_recovery_dialog": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "RecoveryDialogService", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_retry_recoverable_workflow": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "retry preserved workflow state", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_resolve_stale_lock": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "StaleLockRecoveryService", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_rebind_database_artifact_tree": _m(("WorkspaceAdapter", "CorpusAdapter"), "validate artifact tree plus binding registry write", "deferred_to_phase_19"),
        "kernel_discard_or_archive_staged_work": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "StagedWorkArchiveService", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_reconcile_partial_pipeline_run": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "future partial run reconciliation", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "kernel_open_support_bundle": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "SupportBundleService", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "empty_database_no_semantic_release": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "empty_database_default_taxonomy_no_projections": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "empty_database_default_taxonomy_default_projections": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "empty_database_default_taxonomy_custom_projections": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "empty_database_custom_taxonomy_no_projections": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "empty_database_custom_taxonomy_custom_projections": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "manual_pipeline_run": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "create_custom_taxonomy_path": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
        "create_custom_projection_path": _m(KERNEL_INTERNAL_NO_PIPELINE_ADAPTER, "workflow starter", KERNEL_INTERNAL_NO_PIPELINE_ADAPTER),
    }
)


__all__ = ["CANONICAL_FUNCTION_ADAPTER_MAP"]
