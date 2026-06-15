from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    module_key: str
    purpose: str
    working_directory: str
    command: str
    expected_test_scope: str
    blocker_anchor: str = "#full-regression-matrix-pending"
    exit_code: int = 125
    result: str = "blocked"
    timeout_seconds: int = 1800


def _cmd(
    module_key: str,
    purpose: str,
    working_directory: str,
    command: str,
    expected_test_scope: str,
    *,
    timeout_seconds: int = 1800,
) -> CommandSpec:
    return CommandSpec(
        module_key=module_key,
        purpose=purpose,
        working_directory=working_directory,
        command=command,
        expected_test_scope=expected_test_scope,
        timeout_seconds=timeout_seconds,
    )


ROOT_COMMANDS: tuple[CommandSpec, ...] = (
    _cmd("root", "all_dev_tests", ".", 'run-dev-tests.bat --all', "Root full dispatcher regression matrix.", timeout_seconds=10800),
    _cmd("root", "kernel_only", ".", 'run-dev-tests.bat --module kernel --run-only', "Kernel module dispatcher run."),
    _cmd("root", "mcp_only", ".", 'run-dev-tests.bat --module mcp-server --run-only', "MCP Server dispatcher run.", timeout_seconds=7200),
    _cmd("root", "frontend_only", ".", 'run-dev-tests.bat --module frontend --run-only', "Client Frontend dispatcher run."),
)

KERNEL_COMMANDS: tuple[CommandSpec, ...] = (
    _cmd("kernel", "build_runtime", "08 - Semantic Control Kernel", "build-runtime.bat", "Kernel portable runtime build."),
    _cmd("kernel", "check_runtime", "08 - Semantic Control Kernel", "check-runtime.bat", "Kernel runtime preflight."),
    _cmd("kernel", "all_dev_tests", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat", "Kernel full test suite."),
    _cmd("kernel", "phase0_phase1", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase0_scaffold_inventory.py tests\test_phase1_contract_shell.py tests\test_phase1_runtime_preflight.py tests\test_phase1_runtime_manifest.py tests\test_phase1_root_discovery.py", "Kernel scaffold and runtime-shell regression."),
    _cmd("kernel", "phase2", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase2_contract_registry.py tests\test_phase2_contract_roundtrip.py tests\test_phase2_contract_validation.py tests\test_phase2_raw_dict_boundaries.py", "Kernel contract registry and validation."),
    _cmd("kernel", "phase3", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase3_state_layout.py tests\test_phase3_atomic_json_store.py tests\test_phase3_corrupt_quarantine.py tests\test_phase3_resume_store.py tests\test_phase3_lock_store.py tests\test_phase3_receipt_store.py tests\test_phase3_interaction_store.py tests\test_phase3_binding_registry.py tests\test_phase3_truth_boundaries_reset.py", "Kernel repository and state truth rules."),
    _cmd("kernel", "phase4", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase4_adapter_registry.py tests\test_phase4_adapter_mapping_table.py tests\test_phase4_adapter_invocation_contract.py tests\test_phase4_missing_capability_blockers.py tests\test_phase4_false_friend_blocklist.py tests\test_phase4_no_sibling_imports.py tests\test_phase4_no_sibling_filesystem_mutation.py", "Adapter registry and capability blockers."),
    _cmd("kernel", "phase5", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase5_transition_table_parity.py tests\test_phase5_transition_evaluator.py tests\test_phase5_state_resolver_evidence_order.py tests\test_phase5_empty_filled_detection.py tests\test_phase5_target_identity.py tests\test_phase5_attach_activate_separation.py tests\test_phase5_blocker_recovery_mapping.py tests\test_phase5_spec_disagreement.py tests\test_phase5_no_adapter_imports.py", "State transition and resolver parity."),
    _cmd("kernel", "phase6", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase6_interaction_contracts.py tests\test_phase6_frontend_event_sink.py tests\test_phase6_user_surface_mapping.py tests\test_phase6_mirror_events.py tests\test_phase6_recovery_dialogs.py tests\test_phase6_cancellation_and_expiry.py tests\test_phase6_no_agent_value_collection.py", "Kernel interaction and mirror contracts."),
    _cmd("kernel", "phase7", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase7_agent_tool_inventory.py tests\test_phase7_agent_tool_descriptions.py tests\test_phase7_agent_invocation_contract.py tests\test_phase7_event_scoped_recovery_visibility.py tests\test_phase7_support_control_tools.py tests\test_phase7_manifest_actions.py tests\test_phase7_legacy_agent_surface_rejection.py", "Agent-facing tool surface."),
    _cmd("kernel", "phase8", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase8_llm_function_inventory.py tests\test_phase8_provider_boundary.py tests\test_phase8_structured_json_validation.py tests\test_phase8_retry_policy.py tests\test_phase8_update_state_builders_taxonomy.py tests\test_phase8_update_state_builders_projections.py tests\test_phase8_prompt_snapshot_artifacts.py tests\test_phase8_final_validation_failure_mirror.py tests\test_phase8_debug_bundle_redaction.py tests\test_phase8_provider_failure_and_cancel.py tests\test_phase8_report_validation.py tests\test_phase8_no_forbidden_imports.py", "LLM functions, retry and redaction."),
    _cmd("kernel", "phase9", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase9_artifact_tree_contract.py tests\test_phase9_creation_route_sequences.py tests\test_phase9_default_release_paths.py tests\test_phase9_custom_taxonomy_path.py tests\test_phase9_custom_projection_path.py tests\test_phase9_default_taxonomy_no_projection_blocked.py tests\test_phase9_creation_resume.py tests\test_phase9_progress_receipts.py tests\test_phase9_missing_capability_blockers.py tests\test_phase9_no_forbidden_imports.py", "Database creation workflows."),
    _cmd("kernel", "phase11", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase11_pipeline_run_preconditions.py tests\test_phase11_pipeline_run_correlation.py tests\test_phase11_batch_manifest_contract.py tests\test_phase11_reset_database.py tests\test_phase11_manual_pipeline_agent_flow.py", "Pipeline run and reset workflows."),
    _cmd("kernel", "phase12", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase12_merge_entry_routing.py tests\test_phase12_empty_merge_workflow.py tests\test_phase12_filled_merge_workflow.py tests\test_phase12_merge_collision_policy.py tests\test_phase12_merge_collision_manifest.py tests\test_phase12_merge_id_map.py tests\test_phase12_source_identity.py tests\test_phase12_sql_remap.py tests\test_phase12_artifact_fill_policy.py tests\test_phase12_rebuild_workflow.py tests\test_phase12_rebuild_overwrite.py tests\test_phase12_rebuild_embedding_policy.py tests\test_phase12_resume_and_receipts.py tests\test_phase12_no_legacy_merge_tools.py", "Merge and rebuild workflows."),
    _cmd("kernel", "phase13", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase13_semantic_exception_handler.py tests\test_phase13_recovery_matrix.py tests\test_phase13_recovery_tool_schemas.py tests\test_phase13_allowed_agent_tools_lifecycle.py tests\test_phase13_no_permanent_recovery_tool_leakage.py tests\test_phase13_expired_pending_interaction.py tests\test_phase13_stale_lock_recovery.py tests\test_phase13_target_identity_recovery.py tests\test_phase13_partial_pipeline_reconcile.py tests\test_phase13_missing_manifest_originals.py tests\test_phase13_database_artifact_rebind.py tests\test_phase13_staged_work_archive.py tests\test_phase13_merge_collision_recovery.py tests\test_phase13_final_llm_validation_failure.py tests\test_phase13_support_only_terminal.py", "Recovery states and tool exposure."),
    _cmd("kernel", "phase18", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase18_support_bundle_schema.py tests\test_phase18_support_bundle_redaction.py tests\test_phase18_trace_correlation.py tests\test_phase18_adapter_diagnostics.py tests\test_phase18_llm_failure_bundle.py tests\test_phase18_retention_policy.py tests\test_phase18_logs_are_not_truth.py tests\test_phase18_operations_readme.py", "Support bundle and observability."),
    _cmd("kernel", "phase19", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase19_pipeline_owner_capabilities.py tests\test_phase19_adapter_unblock.py tests\test_phase19_pipeline_e2e_smoke.py", "Phase 19 owner capability and adapter unblock evidence."),
    _cmd("kernel", "phase20", "08 - Semantic Control Kernel", r"dev-tests\run-tests.bat tests\test_phase20_go_live_manifest.py tests\test_phase20_regression_command_matrix.py tests\test_phase20_e2e_fixture_matrix.py tests\test_phase20_tool_surface_snapshots.py tests\test_phase20_phase19_evidence.py tests\test_phase20_dead_code_scans.py tests\test_phase20_support_bundle_sample.py tests\test_phase20_readiness_decision.py tests\test_phase20_generator_truth_sources.py", "Phase 20 go-live evidence validation."),
)

MCP_COMMANDS: tuple[CommandSpec, ...] = (
    _cmd("mcp", "build_runtime", "07 - MCP Server", "build-runtime.bat", "MCP runtime build."),
    _cmd("mcp", "check_runtime", "07 - MCP Server", "check-runtime.bat", "MCP runtime preflight."),
    _cmd("mcp", "all_dev_tests", "07 - MCP Server", r"dev-tests\run-tests.bat", "MCP full test suite.", timeout_seconds=7200),
    _cmd("mcp", "bridge_surface", "07 - MCP Server", r"dev-tests\run-tests.bat test_semantic_control_kernel_mcp_catalog.py test_semantic_control_kernel_mcp_dispatch.py test_semantic_control_kernel_mcp_visibility.py test_semantic_control_kernel_event_scoped_recovery.py test_semantic_control_kernel_host_only_client_bridge.py test_semantic_control_kernel_legacy_invisibility.py test_semantic_control_kernel_permissions.py test_semantic_control_kernel_handler_errors.py test_semantic_control_kernel_legacy_inventory.py test_semantic_control_kernel_runtime_manifest.py", "Bridge catalog, visibility and dispatch."),
    _cmd("mcp", "legacy_cleanup", "07 - MCP Server", r"dev-tests\run-tests.bat test_phase15_no_old_kernel_imports.py test_phase15_registry_unlinked.py test_phase15_old_tools_retired.py test_phase15_permissions_semantic_control_kernel.py test_phase15_runtime_manifest_unlinked.py test_phase15_product_semantics_no_workflow_family_ids.py test_phase15_state_is_not_runtime_truth.py test_phase15_non_kernel_tool_regression.py", "Phase 15 unlink regression."),
    _cmd("mcp", "phase16_cleanup", "07 - MCP Server", r"dev-tests\run-tests.bat test_phase16_dead_code_scans.py test_phase16_import_start_smoke.py test_phase16_mcp_tool_catalog_snapshot.py test_phase16_runtime_manifest_clean.py test_phase16_mcp_regression_subset.py test_phase16_new_kernel_surface_regression.py test_phase16_phase14_bridge_regression.py test_phase16_phase15_unlink_regression.py test_phase16_state_policy_enforced.py test_phase16_docs_product_semantics_clean.py test_phase16_client_frontend_blocker_scan.py", "Phase 16 cleanup regression."),
    _cmd("mcp", "go_live_surface", "07 - MCP Server", r"dev-tests\run-tests.bat test_semantic_control_kernel_go_live_surface.py", "Phase 20 MCP go-live surface."),
)

OWNER_COMMANDS: tuple[CommandSpec, ...] = (
    _cmd("orchestrator", "owner_contracts", "00 - Orchestrator", r"dev-tests\run-tests.bat test_kernel_artifact_tree_contract.py test_kernel_batch_manifest_contract.py", "Orchestrator Phase 19 owner capabilities."),
    _cmd("normalizer", "owner_contracts", "04 - Normalizer", r"dev-tests\run-tests.bat test_kernel_semantic_release_domain_service.py", "Normalizer Phase 19 owner capabilities."),
    _cmd("corpus", "owner_contracts", "05 - Corpus Builder", r"dev-tests\run-tests.bat test_kernel_artifact_tree_contract.py test_kernel_multi_source_merge_domain_service.py", "Corpus Builder Phase 19 owner capabilities."),
)

FRONTEND_COMMANDS: tuple[CommandSpec, ...] = (
    _cmd("frontend", "check_runtimes", "Client Frontend", r"node\node.exe --disable-warning=ExperimentalWarning tools\check-runtimes.mjs", "Client Frontend runtime check."),
    _cmd("frontend", "build", "Client Frontend", r"node\node.exe node_modules\vite\bin\vite.js build", "Client Frontend production build."),
    _cmd("frontend", "all_dev_tests", "Client Frontend", r"dev-tests\run-tests.bat", "Client Frontend full test suite."),
    _cmd("frontend", "kernel_surface", "Client Frontend", r"dev-tests\run-tests.bat dev-tests\tests\pipeline-agent-tool-surface.test.js dev-tests\tests\pipeline-agent-workflow.test.js dev-tests\tests\pipeline-agent-context.test.js dev-tests\tests\pipeline-agent-mirror-events.test.js dev-tests\tests\pipeline-agent-recovery-tools.test.js dev-tests\tests\pipeline-agent-legacy-surface-rejection.test.js dev-tests\tests\http-pipeline-manager-kernel-events.test.js dev-tests\tests\main-app-kernel-dialogs.test.js dev-tests\tests\main-app-kernel-progress.test.js dev-tests\tests\main-app-kernel-recovery.test.js", "Client Frontend kernel integration regression."),
    _cmd("frontend", "go_live_surface", "Client Frontend", r"dev-tests\run-tests.bat dev-tests\tests\pipeline-agent-go-live-surface.test.js dev-tests\tests\main-app-go-live-kernel-events.test.js", "Client Frontend Phase 20 go-live regression."),
)

SCAN_COMMANDS: tuple[CommandSpec, ...] = (
    _cmd("scan", "legacy_patterns", ".", r'rg -n "mcp_server\.semantic_kernel|from \.semantic_kernel|mcp_server/semantic_kernel|tool_catalog_semantic_kernel|tool_handlers_semantic_kernel|KERNEL_TOOL_NAMES|llm_action_catalog|open_workflow|inspect_workflow|execute_readonly_workflow_action|execute_author_workflow_action|execute_operator_workflow_action|execute_admin_workflow_action|interrupt_workflow|close_workflow|workflow_family_id|workflow_revision|action_token|target_action_id|x_action_catalog|required_agent_level|permission-level execute" "07 - MCP Server/mcp_server" "07 - MCP Server/config" "07 - MCP Server/runtime" "07 - MCP Server/module-manifest.json" "07 - MCP Server/README.md" "Client Frontend/client_frontend" "Client Frontend/server" "Client Frontend/src" "Client Frontend/README.md" "08 - Semantic Control Kernel/semantic_control_kernel" "08 - Semantic Control Kernel/module-manifest.json" "08 - Semantic Control Kernel/README.md"', "Active-root dead-code scan."),
    _cmd("scan", "recovery_leakage", ".", r'rg -n "kernel_apply_recovery_option|kernel_open_recovery_dialog|kernel_retry_recoverable_workflow|kernel_resolve_stale_lock|kernel_rebind_database_artifact_tree|kernel_discard_or_archive_staged_work|kernel_reconcile_partial_pipeline_run|kernel_open_support_bundle" "Client Frontend/client_frontend/pipeline_agent" "Client Frontend/dev-tests/tests" "07 - MCP Server/mcp_server"', "Recovery-tool leakage scan."),
)

ALL_COMMANDS: tuple[CommandSpec, ...] = ROOT_COMMANDS + KERNEL_COMMANDS + MCP_COMMANDS + OWNER_COMMANDS + FRONTEND_COMMANDS + SCAN_COMMANDS
