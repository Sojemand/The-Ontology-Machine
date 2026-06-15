# Semantic Runtime Kernel Components

This folder is the current componentized Semantic Control Kernel specification surface.

## Component Index

- [01 Kernel Scope, State, And Terminology](01_kernel_scope_state_terminology.md)
- [02 Kernel State Transition Table](02_kernel_state_transition_table.md)
- [03 Database Provenance And Merge Policy](03_database_provenance_and_merge_policy.md)
- [04 LLM Artifact Transition Table](04_llm_artifact_transition_table.md)
- [05 Database Creation Workflows](05_database_creation_workflows.md)
- [06 Retired Modify Family Notice](06_database_modification_workflows.md)
- [07 Pipeline, Merge, And Rebuild Workflows](07_pipeline_merge_rebuild_workflows.md)
- [08 User Function Surface](08_user_function_surface.md)
- [09 Action Pathways](09_action_pathways.md)
- [10 Kernel Only Functions](10_kernel_only_functions.md)
- [11 Kernel Internal Data Contracts](11_kernel_internal_data_contracts.md)
- [12 Shared LLM Contract Rules](12_shared_llm_contract_rules.md)
- [13 LLM Analyze Samples](13_llm_analyze_samples.md)
- Retired LLM notices are kept as stub files only, not active component entries.
- [15 LLM User Reports](15_llm_user_reports.md)
- [16 LLM Create Projections From Sample Analyses](16_llm_create_projections_from_samples.md)
- [17 LLM Create Taxonomy From Sample Analyses](17_llm_create_taxonomy_from_samples.md)
- [22 MCP Kernel Pipeline Function Contract](22_mcp_kernel_pipeline_function_contract.md)
- [23 Agent Facing Pipeline Manager Tools](23_agent_facing_pipeline_manager_tools.md)

## Current Authority

As of 2026-05-31, the Kernel has no DB modify family. The live permanent surface is the 16-tool list in `08_user_function_surface.md`, `module-manifest.json`, MCP visibility config and the Client Frontend Kernel client.

The old monolith split source is retained only as retired context; this component folder is kept current directly.
