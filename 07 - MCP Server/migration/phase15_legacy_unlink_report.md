# Phase 15 Legacy Kernel Unlink Report

- drift_preflight: build_plan_authority_applied
  - `SPEC_Semantic_Control_Kernel_Build.md` now uses the live Phase 14/15 bridge classification name `legacy_hidden` for retired old-Kernel names.
  - `migration/phase14_legacy_cleanup_inventory.json` still classifies several old tests broadly as `rewrite_in_phase_15`; Phase 15 refines those files into explicit rewrite, replacement or Phase 16 deletion dispositions in `phase15_legacy_test_disposition.json`.

## Rewritten Files

- `mcp_server/product_semantics.py`
- `mcp_server/product_semantics_support.py`
- `mcp_server/product_semantics_playbooks.py`
- `mcp_server/product_semantics_cards.py`
- `mcp_server/permission_defaults.py`
- `config/agent_permissions.json`
- `runtime/runtime-manifest.json`
- `mcp_server/semantic_control_kernel_visibility.py`
- `README.md`
- rewritten MCP Server regression tests and new Phase 15 tests under `dev-tests/tests/`

## Removed Legacy Dependencies

- MCP product code no longer imports `mcp_server.semantic_kernel`.
- MCP product code no longer imports `KERNEL_TOOL_NAMES`, `tool_catalog_semantic_kernel` or `tool_handlers_semantic_kernel`.
- Product semantics no longer imports the old workflow-family catalog or proposal-text helpers.
- Permanent permissions no longer mention `llm_action_catalog`, `open_workflow`, `inspect_workflow`, `execute_*_workflow_action`, `interrupt_workflow` or `close_workflow`.
- Runtime packaging no longer requires `mcp_server/semantic_kernel/**`, `tool_catalog_semantic_kernel.py` or `tool_handlers_semantic_kernel.py`.
- Live Phase 15 scan found and removed one additional old-package import in `mcp_server/tool_handler_source_sample_set_paths.py`.
- Direct calls to hidden `kernel_internal` and `kernel_continuation_scoped` names now fail closed at the public MCP boundary before bridge dispatch.
- Direct calls to event-scoped recovery names now require Kernel bridge confirmation that the mirror/recovery/snapshot scope is active and exposes the exact requested tool before the MCP registry dispatches the handler.

## Current Stronger End State

- The old `mcp_server/semantic_kernel/` package and the temporary Phase 15 shim
  files are already physically removed in the current repo state.
- Phase 15 compliance therefore depends on the surviving unlink truth
  boundaries, not on preserving compatibility marker files.
- No deleted legacy files were recreated during this audit.

## Legacy State Handling

- See `phase15_legacy_state_policy.md`.
- Observed legacy state root remained untouched at `state/semantic_kernel/`.
- Legacy state is historical evidence only and is not active runtime truth for the Semantic Control Kernel bridge.

## Tests Run

Historical verification entries are retained below. The current audit reran the
hidden-scope/public-boundary subset and the Phase 15 unlink subset after the
fail-closed repair.

- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_tool_handlers_product_advisory.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_agent_permissions.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_contract_healthcheck.py tests\test_protocol.py tests\test_semantic_control_kernel_permissions.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_semantic_control_kernel_mcp_catalog.py tests\test_semantic_control_kernel_mcp_dispatch.py tests\test_semantic_control_kernel_mcp_visibility.py tests\test_semantic_control_kernel_event_scoped_recovery.py tests\test_semantic_control_kernel_host_only_client_bridge.py tests\test_semantic_control_kernel_legacy_invisibility.py tests\test_semantic_control_kernel_permissions.py tests\test_semantic_control_kernel_handler_errors.py tests\test_semantic_control_kernel_legacy_inventory.py tests\test_semantic_control_kernel_runtime_manifest.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_phase15_no_old_kernel_imports.py tests\test_phase15_registry_unlinked.py tests\test_phase15_old_tools_retired.py tests\test_phase15_hidden_scope_fail_closed.py tests\test_phase15_permissions_semantic_control_kernel.py tests\test_phase15_runtime_manifest_unlinked.py tests\test_phase15_product_semantics_no_workflow_family_ids.py tests\test_phase15_state_is_not_runtime_truth.py tests\test_phase15_non_kernel_tool_regression.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_tool_subprocess_core.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_tool_contract_matrix_golden.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_semantic_control_kernel_legacy_inventory.py tests\test_phase15_no_old_kernel_imports.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_semantic_control_kernel_mcp_dispatch.py tests\test_phase15_hidden_scope_fail_closed.py tests\test_phase15_old_tools_retired.py tests\test_protocol.py tests\test_phase15_registry_unlinked.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_phase15_hidden_scope_fail_closed.py tests\test_semantic_control_kernel_mcp_dispatch.py tests\test_semantic_control_kernel_event_scoped_recovery.py tests\test_semantic_control_kernel_mcp_visibility.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_phase15_no_old_kernel_imports.py tests\test_phase15_registry_unlinked.py tests\test_phase15_old_tools_retired.py tests\test_phase15_hidden_scope_fail_closed.py tests\test_phase15_permissions_semantic_control_kernel.py tests\test_phase15_runtime_manifest_unlinked.py tests\test_phase15_product_semantics_no_workflow_family_ids.py tests\test_phase15_state_is_not_runtime_truth.py tests\test_phase15_non_kernel_tool_regression.py -q`
- Pass: `dev-tests\.venv\python.exe -m pytest tests\test_semantic_control_kernel_mcp_catalog.py tests\test_semantic_control_kernel_mcp_dispatch.py tests\test_semantic_control_kernel_mcp_visibility.py tests\test_semantic_control_kernel_event_scoped_recovery.py tests\test_semantic_control_kernel_host_only_client_bridge.py tests\test_semantic_control_kernel_legacy_invisibility.py tests\test_semantic_control_kernel_permissions.py tests\test_semantic_control_kernel_handler_errors.py tests\test_semantic_control_kernel_legacy_inventory.py tests\test_semantic_control_kernel_runtime_manifest.py -q`

Note:
- The current `dev-tests\run-tests.bat` wrapper prepends the whole `tests/` tree before extra args, so Phase 15 verification used the module dev-test venv directly to run the exact subsets named by the build spec.

## Historical Phase 16 Deletion Prerequisites

- Delete `mcp_server/semantic_kernel/` only after Phase 15 unlink tests stay green.
- Delete `mcp_server/tool_catalog_semantic_kernel.py` and `mcp_server/tool_handlers_semantic_kernel.py` after confirming no active product import, registry entry, permission entry or runtime-manifest entry remains.
- Remove old `test_semantic_kernel*.py` files according to `phase15_legacy_test_disposition.json`.
- Keep `phase15_legacy_state_policy.md` available until a separate explicit archival or deletion decision for `state/semantic_kernel/` is made.
- Current repo status: the legacy package and the temporary shim files are
  already deleted, so these prerequisites remain as historical evidence only.
