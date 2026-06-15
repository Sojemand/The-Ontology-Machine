# Phase 14 MCP Cutover

Cutover commit or tag: `PHASE14_CUTOVER_COMMIT`

## Summary

- Normal MCP `tools/list` now exposes the Semantic Control Kernel permanent
  workflow/support surface through `tool_catalog_semantic_control_kernel.py`.
- The MCP Server calls the Kernel only through the local subprocess contract in
  `semantic_control_kernel_client.py`.
- Host-only Client Frontend bridge operations live in
  `semantic_control_kernel_client_frontend_bridge.py` and are not Agent tools.

## New Files Added

- `mcp_server/semantic_control_kernel_client.py`
- `mcp_server/semantic_control_kernel_client_frontend_bridge.py`
- `mcp_server/semantic_control_kernel_visibility.py`
- `mcp_server/semantic_control_kernel_legacy_inventory.py`
- `mcp_server/tool_catalog_semantic_control_kernel.py`
- `mcp_server/tool_handlers_semantic_control_kernel.py`
- `config/semantic_control_kernel_bridge.json`

## Hidden Legacy Files

- `mcp_server/tool_catalog_semantic_kernel.py`
- `mcp_server/tool_handlers_semantic_kernel.py`
- `mcp_server/semantic_kernel/`

These files remain in the repository only as hidden legacy payload until Phase
15 unlinks the remaining references and Phase 16 deletes them.

## Rollback Note

- Rollback is a repository operation, not a runtime compatibility switch.
- Allowed rollback:
  - revert the Phase 14 commit
  - check out the pre-cutover tag or branch for isolated investigation
  - disable the Semantic Control Kernel MCP bridge and surface a maintenance error
- Disallowed rollback:
  - re-enabling `llm_action_catalog`, `open_workflow`, `inspect_workflow` or
    `execute_*_workflow_action` in normal Agent operation
  - running old and new Kernel routing in parallel
  - translating workflow-family sessions into new Kernel state in MCP glue

## Test Commands

- `pytest dev-tests/tests/test_semantic_control_kernel_mcp_catalog.py`
- `pytest dev-tests/tests/test_semantic_control_kernel_mcp_dispatch.py`
- `pytest dev-tests/tests/test_semantic_control_kernel_mcp_visibility.py`
- `pytest dev-tests/tests/test_semantic_control_kernel_event_scoped_recovery.py`
- `pytest dev-tests/tests/test_semantic_control_kernel_host_only_client_bridge.py`

Legacy Agent routing must not be restored in normal operation because it would
reintroduce retired workflow-family routing truth and permission-level execute
surfaces that Phase 14 explicitly removes.
