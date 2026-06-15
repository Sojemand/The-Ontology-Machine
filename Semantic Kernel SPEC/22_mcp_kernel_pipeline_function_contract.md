# MCP Kernel Pipeline Function Contract

MCP exposes the current Semantic Control Kernel through a small governed surface. The Kernel remains the canonical owner of workflow semantics; MCP and Client Frontend surfaces must mirror the same 16 permanent tool names.

Canonical MCP-Facing Kernel Surface
	- create_standard_artifact_folder_tree
	- create_empty_database
	- store_active_artifact_folder_tree
	- reset_database
	- write_semantic_release
	- attach_semantic_release_to_database
	- attach_default_semantic_release_to_database
	- attach_custom_semantic_release_to_database
	- activate_semantic_release
	- stage_custom_taxonomy_for_semantic_release
	- stage_custom_projections_for_semantic_release
	- create_custom_semantic_release
	- create_custom_taxonomy
	- create_custom_projection
	- validate_projections_against_taxonomy
	- pipeline_run
	- database_merge_additive_only
	- empty_databases_merge_path
	- filled_databases_merge_path
	- merge_database_empty
	- merge_database_filled_additive
	- merge_taxonomy_and_projections_additive
	- reconcile_merged_semantic_release
	- reconcile_merged_database
	- write_combined_database
	- fill_artifact_folder_tree
	- backfill_sql
	- database_rebuild_from_artifacts
	- corpus_builder_load_semantic_release
	- run_corpus_builder
	- create_embeddings
	- kernel_status
	- kernel_resume_state
	- kernel_continue_resumable_workflow
	- kernel_cancel_active_run
	- kernel_apply_recovery_option
	- kernel_open_recovery_dialog
	- kernel_retry_recoverable_workflow
	- kernel_resolve_stale_lock
	- kernel_rebind_database_artifact_tree
	- kernel_discard_or_archive_staged_work
	- kernel_reconcile_partial_pipeline_run
	- kernel_open_support_bundle
	- empty_database_no_semantic_release
	- empty_database_default_taxonomy_no_projections
	- empty_database_default_taxonomy_default_projections
	- empty_database_default_taxonomy_custom_projections
	- empty_database_custom_taxonomy_no_projections
	- empty_database_custom_taxonomy_custom_projections
	- manual_pipeline_run
	- create_custom_taxonomy_path
	- create_custom_projection_path

Workflow entry route exposure

## Permanent Agent-Visible Kernel Tools

- `empty_database_no_semantic_release`
- `empty_database_default_taxonomy_no_projections`
- `empty_database_default_taxonomy_default_projections`
- `empty_database_default_taxonomy_custom_projections`
- `empty_database_custom_taxonomy_no_projections`
- `empty_database_custom_taxonomy_custom_projections`
- `manual_pipeline_run`
- `database_merge_additive_only`
- `database_rebuild_from_artifacts`
- `create_custom_taxonomy_path`
- `create_custom_projection_path`
- `reset_database`
- `kernel_status`
- `kernel_resume_state`
- `kernel_continue_resumable_workflow`
- `kernel_cancel_active_run`

## Hidden Or Internal Routes

- `pipeline_run` is internal to `manual_pipeline_run`.
- Empty/filled merge routes are internal to `database_merge_additive_only`.
- Recovery operations are event-scoped and must be bound by a Kernel mirror event before exposure.

## Pipeline Adapter Boundary

- `WorkspaceAdapter` creates Artifact Tree folders.
- `CorpusAdapter` creates, resets, rebuilds, activates and merges Corpus DB state through owner contracts.
- `SemanticReleaseAdapter` exports, stages, materializes, writes, attaches and activates Semantic Release packages.
- `MergeAdapter` performs additive multi-source merge owner calls.
- `PipelineBatchAdapter` creates and finalizes batch manifests for manual pipeline runs.
- `OrchestratorAdapter` runs ingestion for the internal `pipeline_run` route.

## Removed Scope

MCP must reject old DB modify-family names as unknown actions. No cleanup/reimport continuation tool exists in permanent, normal, event-scoped or host-only visibility. Product guidance must recommend rebuild, merge, reset, custom creation paths or manual pipeline run instead.
