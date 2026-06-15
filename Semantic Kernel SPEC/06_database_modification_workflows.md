# Retired Modify Family Notice

The DB modify family was removed from the live Semantic Control Kernel on 2026-05-31.

No workflow in this family is Agent-facing, MCP-visible, continuation-scoped, host-only or Kernel-internal live behavior. Existing frozen workflow artifacts may still contain historic next-action labels for compatibility; those frozen artifacts are not authority for new dispatch, registry, documentation or product guidance.

Use the live alternatives instead:

- Create a new semantic release path with `create_custom_taxonomy_path` or `create_custom_projection_path` during database creation.
- Run ingestion with `manual_pipeline_run`.
- Rebuild from artifacts with `database_rebuild_from_artifacts`.
- Merge databases additively with `database_merge_additive_only`.
- Reset intentionally with `reset_database`.
