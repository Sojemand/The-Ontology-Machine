# Action Pathways

The live Kernel action pathways are intentionally small. The old DB modify family is retired.

## Permanent Agent-Visible Starters

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

## Internal Routes

- Empty and filled merge paths are selected only inside `database_merge_additive_only`.
- `pipeline_run` is an internal route behind `manual_pipeline_run`.
- Recovery tools are event-scoped and may appear only when a Kernel mirror event binds them.

## Frozen Compatibility

Frozen workflow records may contain historic labels in final notices. Those labels must not be reintroduced into manifests, MCP visibility, Client Frontend permanent tools or dispatch.
