# Kernel Only Functions

This file describes the current Kernel-owned functions after the 2026-05-31 modify-family removal.

## Canonical Permanent Surface

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

## Kernel-Internal Functions

- `pipeline_run`: internal ingestion route invoked by `manual_pipeline_run` after Kernel-owned path selection, Input confirmation, active database proof and active Semantic Release proof.
- `empty_databases_merge_path`: internal semantic-only merge route selected by `database_merge_additive_only` when all sources are empty.
- `filled_databases_merge_path`: internal additive data merge route selected by `database_merge_additive_only` when any source is filled.
- `continue_workflow_after_interaction`: host bridge continuation entry for pending Kernel-owned user interactions.
- `cancel_active_workflow`: stateful cancellation path behind `kernel_cancel_active_run`.

## Services

- `KernelStateResolver` proves active database, artifact tree, semantic release and blockers.
- `KernelUserInteractionService` owns dialogs and validates responses.
- `ConfirmationService`, `ReceiptStore`, `LockStore` and `WorkflowResumeStore` own mutation safety and resumability.
- `KernelMirrorEventService` emits progress, final notices and event-scoped recovery affordances.
- `AnalysisArtifactStore`, `PromptSnapshotStore`, `LLMFunctionAdapter` and the update-state builders support creation-time custom taxonomy/projection authoring only.
- `PipelineBatchAdapter` owns pending/final batch manifest provenance for manual pipeline runs.

## Removed Scope

Existing-database taxonomy/projection modification, cleanup/reimport loops and database-analysis comparison routes are not Kernel-only functions anymore. Do not add them to dispatch, schemas, state tables, MCP visibility, Client Frontend permanent tools or product guidance.
