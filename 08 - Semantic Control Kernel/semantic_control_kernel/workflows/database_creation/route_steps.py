from __future__ import annotations

from types import MappingProxyType

from semantic_control_kernel.workflows.database_creation.route_types import (
    KERNEL_BOOKKEEPING,
    PHASE6_INTERACTION,
    READ_BUILD_SOURCE_STEP,
    SPEC04_LLM_TRANSITION,
    SPEC11_DETERMINISTIC_TRANSFORM,
    DatabaseCreationStep,
)


_s = DatabaseCreationStep

STEP_CATALOG: tuple[DatabaseCreationStep, ...] = (
    _s("dc_collect_target", "open creation target interaction", PHASE6_INTERACTION, "UserInteractionAdapter", "none", "kernel.database_creation_target.v1 in workflow state", "awaiting_creation_target", "before target selection"),
    _s("dc_create_artifact_tree", "create_standard_artifact_folder_tree", "tr_001", "WorkspaceAdapter.prepare_artifact_tree", "valid target and no conflict", "canonical Artifact Tree folders", "artifact_tree_created", "after folder creation"),
    _s("dc_store_artifact_tree", "store_active_artifact_folder_tree", KERNEL_BOOKKEEPING, "WorkspaceAdapter.validate_artifact_tree plus ActiveArtifactTreeRefStore", "created Artifact Tree paths", "Kernel active Artifact Tree reference", "artifact_tree_verified", "after verification"),
    _s("dc_create_empty_database", "create_empty_database", "tr_002", "CorpusAdapter.create_empty_database", "verified Artifact Tree and Corpus database path", "empty Corpus database plus kernel.database_artifact_binding.v1", "empty_database_created", "after database creation"),
    _s("dc_export_default_release", "resolve default Semantic Release source", READ_BUILD_SOURCE_STEP, "SemanticReleaseAdapter.export_default_semantic_release", "runtime blueprint ref or fixture", "kernel.default_semantic_release_ref.v1", "default_release_resolved", "after default export"),
    _s("dc_write_default_release", "write_semantic_release for default package", "tr_006", "SemanticReleaseAdapter.write_semantic_release", "complete default release ref", "Semantic Release/releases/<release_id>/", "default_release_written", "after write"),
    _s("dc_attach_default_release", "attach_default_semantic_release_to_database", "tr_004", "SemanticReleaseAdapter.load_semantic_release plus Kernel attach state", "written complete default release and database proof", "kernel.semantic_release_attach_state.v1", "default_release_attached", "after attach"),
    _s("dc_remove_default_projections", "remove_projection_from_database for all default projections", "tr_008", "SemanticReleaseAdapter.remove_taxonomy_or_projection", "attached complete default release and route confirmation", "taxonomy-only staged/incomplete release evidence", "default_projections_removed", "after incomplete taxonomy-only state"),
    _s("dc_activate_default_release", "activate_semantic_release", "tr_007", "SemanticReleaseAdapter.preflight_semantic_release_activation plus activate_semantic_release", "complete attached default release", "active runtime release proof", "semantic_release_activated", "after activation"),
    _s("tax_require_samples", "require sample files for taxonomy authoring", PHASE6_INTERACTION, "select_sample_files plus Orchestrator/Optimizer sample inspection", "Artifact Tree Input path", "kernel.analyze_sample.input.v1 sample evidence", "awaiting_sample_files", "before sample analysis"),
    _s("tax_analyze_samples", "analyze_samples", SPEC04_LLM_TRANSITION, "Phase 8 LLM function port", "sample file evidence", "kernel.sample_analyses.v1", "samples_analyzed", "after sample analysis"),
    _s("tax_create_proposal", "create_taxonomy_to_sample_analyses", SPEC04_LLM_TRANSITION, "Phase 8 LLM function port", "validated kernel.sample_analyses.v1", "kernel.taxonomy_to_sample_analyses.v1", "taxonomy_proposal_created", "after proposal"),
    _s("tax_build_update_state", "create_taxonomy_update_state", SPEC04_LLM_TRANSITION, "UpdateStateBuilder", "validated kernel.taxonomy_to_sample_analyses.v1", "kernel.create_taxonomy_update_state.input.v1", "taxonomy_update_state_created", "after update-state"),
    _s("tax_create_custom_taxonomy", "create_custom_taxonomy", "tr_012", "SemanticReleaseAdapter.stage_taxonomy or materialize primitive", "valid creation taxonomy update-state", "custom taxonomy artifact", "custom_taxonomy_created", "after custom taxonomy"),
    _s("tax_stage_custom_taxonomy", "stage_custom_taxonomy_for_semantic_release", "tr_009", "SemanticReleaseAdapter.stage_taxonomy", "custom taxonomy artifact and Semantic Release folder", "Semantic Release/staged/taxonomy/<taxonomy_stage_id>/", "custom_taxonomy_staged", "after staged taxonomy"),
    _s("proj_require_taxonomy", "resolve taxonomy for projection authoring", KERNEL_BOOKKEEPING, "Kernel state resolver", "staged taxonomy, active taxonomy or attached taxonomy", "taxonomy ref in workflow state", "projection_taxonomy_resolved", "before authoring view"),
    _s("proj_require_samples", "require sample files for projection authoring", PHASE6_INTERACTION, "select_sample_files plus Orchestrator/Optimizer sample inspection", "Artifact Tree Input path", "kernel.analyze_sample.input.v1 sample evidence", "awaiting_projection_samples", "before sample analysis"),
    _s("proj_build_authoring_view", "build kernel.taxonomy_projection_authoring_view.v1", SPEC11_DETERMINISTIC_TRANSFORM, "Kernel deterministic builder", "real taxonomy ref and sample scope", "tax_view.json", "taxonomy_authoring_view_created", "after authoring view"),
    _s("proj_analyze_samples", "analyze_samples or reuse compatible analysis", SPEC04_LLM_TRANSITION, "Phase 8 LLM function port", "sample file evidence", "kernel.sample_analyses.v1 ref", "projection_samples_analyzed", "after sample analysis"),
    _s("proj_create_proposal", "create_projections_to_sample_analyses", SPEC04_LLM_TRANSITION, "Phase 8 LLM function port", "sample analyses plus taxonomy authoring view", "kernel.projections_to_sample_analyses.v1", "projection_proposal_created", "after proposal"),
    _s("proj_build_update_state", "create_projections_update_state", SPEC04_LLM_TRANSITION, "UpdateStateBuilder", "validated projection proposal and real taxonomy", "kernel.create_projections_update_state.input.v1", "projection_update_state_created", "after update-state"),
    _s("proj_create_custom_projection", "create_custom_projection", "tr_013", "SemanticReleaseAdapter.stage_projections or materialize primitive", "valid creation projection update-state", "custom projection artifacts", "custom_projections_created", "after custom projections"),
    _s("proj_validate_projection", "validate_projections_against_taxonomy", "tr_014", "SemanticReleaseAdapter.validate_projections_against_taxonomy", "custom projections and exact taxonomy ref", "validation result", "custom_projections_validated", "after validation"),
    _s("proj_stage_custom_projection", "stage_custom_projections_for_semantic_release", "tr_010", "SemanticReleaseAdapter.stage_projections", "validated custom projections and taxonomy", "Semantic Release/staged/projections/<projection_stage_id>/", "custom_projections_staged", "after staged projections"),
    _s("rel_create_custom_release", "create_custom_semantic_release", "tr_011", "SemanticReleaseAdapter.create_custom_semantic_release", "staged taxonomy and validated staged projections", "detached complete custom release ref", "custom_release_created", "after release creation"),
    _s("rel_write_custom_release", "write_semantic_release for custom package", "tr_006", "SemanticReleaseAdapter.write_semantic_release", "complete custom release ref and Semantic Release folder", "Semantic Release/releases/<release_id>/", "custom_release_written", "after write"),
    _s("rel_attach_custom_release", "attach_custom_semantic_release_to_database", "tr_005", "SemanticReleaseAdapter.load_semantic_release plus Kernel attach state", "written complete custom release and database proof", "kernel.semantic_release_attach_state.v1", "custom_release_attached", "after attach"),
    _s("rel_activate_custom_release", "activate_semantic_release", "tr_007", "SemanticReleaseAdapter.preflight_semantic_release_activation plus activate_semantic_release", "complete attached custom release", "active runtime release proof", "custom_release_activated", "after activation"),
    _s("rel_persist_incomplete_state", "persist incomplete release marker and resume context", KERNEL_BOOKKEEPING, "Kernel repository", "staged evidence or missing release reason", "incomplete_semantic_release.json and kernel.workflow_resume_state.v1", "semantic_release_incomplete_staged", "final blocked state"),
    _s("dc_final_notice", "emit final workflow completion or blocked-state notice", PHASE6_INTERACTION, "KernelMirrorEventService", "final state snapshot", "mirror/progress event", "workflow_final_notice", "no resume unless blocked"),
)

STEP_BY_ID = MappingProxyType({step.step_id: step for step in STEP_CATALOG})
