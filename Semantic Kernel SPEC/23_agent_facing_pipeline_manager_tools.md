# Agent Facing Pipeline Manager Tools

The Pipeline Manager Agent receives only the current Semantic Control Kernel permanent surface plus event-scoped recovery tools explicitly bound by Kernel mirror events.

## Permanent Tools

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

## Event-Scoped Tools

- `kernel_open_recovery_dialog`
- `kernel_open_support_bundle`
- `kernel_cancel_active_run`

Event-scoped tools are available only while the associated mirror event says so. They are never a substitute for permanent workflow tools.

## Product Guidance

- For new or adjusted semantic structure, create a new custom taxonomy/projection path during database creation.
- For changed data inputs, use `manual_pipeline_run` or `database_rebuild_from_artifacts` depending on whether the existing Artifact Tree remains authoritative.
- For combining sources, use `database_merge_additive_only`.
- For a deliberate clean slate, use `reset_database`.
- Do not recommend retired modify, cleanup or reimport flows.
