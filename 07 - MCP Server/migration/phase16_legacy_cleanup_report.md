# Phase 16 Legacy Cleanup Report

Phase 16 status: complete

- drift_preflight: build_plan_authority_applied
  - Phase 16 requires fail-closed handling for retired MCP Kernel names, but it also requires dead-code scans to remove raw legacy routing strings from active product surfaces. The active MCP helper files were rewritten to preserve fail-closed behavior while removing raw legacy literals from product/runtime/docs paths.
  - The follow-up cleanup decision removes the legacy MCP state-root expectation. Phase 16 evidence is kept in committed migration artifacts, not in mutable `state/` leftovers.

## Preconditions

- Phase 15 hard gate passed:
  - `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase15_no_old_kernel_imports.py tests\\test_phase15_old_tools_retired.py tests\\test_phase15_registry_unlinked.py tests\\test_phase15_permissions_semantic_control_kernel.py tests\\test_phase15_runtime_manifest_unlinked.py tests\\test_phase15_product_semantics_no_workflow_family_ids.py tests\\test_phase15_state_is_not_runtime_truth.py tests\\test_phase15_non_kernel_tool_regression.py -q`
  - exit status: `0`
  - summary: `12 passed`
- `phase15_legacy_unlink_report.md` exists and names no unresolved production import.
- `phase15_legacy_test_disposition.json` exists and classifies every old `test_semantic_kernel*` file.
- `phase15_legacy_state_policy.md` exists and records that the legacy MCP state root is no longer expected.
- `runtime/runtime-manifest.json` was already unlinked from the old package before deletion.

## Deleted Paths

- Directory count: `1`
- File count: `28`
- Deleted directory:
  - `mcp_server/semantic_kernel/`
- Deleted files:
  - `mcp_server/tool_catalog_semantic_kernel.py`
  - `mcp_server/tool_handlers_semantic_kernel.py`
  - `dev-tests/tests/semantic_kernel_spec_helpers.py`
  - `dev-tests/tests/test_semantic_kernel_capabilities.py`
  - `dev-tests/tests/test_semantic_kernel_catalog.py`
  - `dev-tests/tests/test_semantic_kernel_current_environment.py`
  - `dev-tests/tests/test_semantic_kernel_document_set_refinement.py`
  - `dev-tests/tests/test_semantic_kernel_end_to_end.py`
  - `dev-tests/tests/test_semantic_kernel_errors.py`
  - `dev-tests/tests/test_semantic_kernel_event_log.py`
  - `dev-tests/tests/test_semantic_kernel_execute.py`
  - `dev-tests/tests/test_semantic_kernel_exports.py`
  - `dev-tests/tests/test_semantic_kernel_human_response.py`
  - `dev-tests/tests/test_semantic_kernel_inspector.py`
  - `dev-tests/tests/test_semantic_kernel_inspector_authority.py`
  - `dev-tests/tests/test_semantic_kernel_inspector_guards.py`
  - `dev-tests/tests/test_semantic_kernel_intake_policy.py`
  - `dev-tests/tests/test_semantic_kernel_interrupts.py`
  - `dev-tests/tests/test_semantic_kernel_mcp_surface.py`
  - `dev-tests/tests/test_semantic_kernel_product_advisory.py`
  - `dev-tests/tests/test_semantic_kernel_races.py`
  - `dev-tests/tests/test_semantic_kernel_release_refinement.py`
  - `dev-tests/tests/test_semantic_kernel_roundtrip.py`
  - `dev-tests/tests/test_semantic_kernel_secret_execute.py`
  - `dev-tests/tests/test_semantic_kernel_secret_fingerprints.py`
  - `dev-tests/tests/test_semantic_kernel_source_fit.py`
  - `dev-tests/tests/test_semantic_kernel_state.py`
  - `dev-tests/tests/test_semantic_kernel_tool_coverage.py`
- The deleted legacy package directory also removed generated `__pycache__` payloads nested under that retired tree.

## Rewritten Paths

- `README.md`
  - removed raw legacy tool-name, deleted-file and old-state-path references from active documentation
  - kept only canonical Semantic Control Kernel bridge language
- `mcp_server/semantic_control_kernel_visibility.py`
  - preserved fail-closed retired-name rejection
  - removed raw legacy routing strings from active product code
- `mcp_server/semantic_control_kernel_legacy_inventory.py`
  - preserved historical inventory generation for Phase 14 evidence
  - removed raw legacy routing strings from active product code
- `mcp_server/tool_handler_source_fit_review.py`
- `mcp_server/tool_handler_source_sample_set_review.py`
- `mcp_server/tool_handlers_source_fit.py`
- `mcp_server/tool_handlers_source_sample_set.py`
- `mcp_server/tool_handler_corpus_reimport_plan.py`
- `mcp_server/tool_handlers_corpus_reimport.py`
  - replaced stale workflow-family follow-up fields with canonical Kernel tool guidance fields
- `migration/phase16_legacy_deletion_manifest.json`
- `migration/phase16_legacy_cleanup_report.md`
- new Phase 16 verification tests under `dev-tests/tests/test_phase16_*.py`

## State Handling

- Cleanup decision applied:
  - `Result: removed; legacy MCP Kernel state is no longer expected in this repository.`
  - `07 - MCP Server/state/semantic_kernel/ is not a supported runtime or historical fixture after the cleanup decision.`
  - `No test or runtime path may require 07 - MCP Server/state/semantic_kernel/ to exist.`
- Phase 16 action:
  - did not migrate or merge any legacy sessions, locks, events or funnels into the new Kernel stores
  - verified the legacy MCP state root is absent
  - verified the MCP bridge and active docs do not read or require the legacy state path

## Generated Artifacts

- Generated artifacts removed with the deleted legacy package directory:
  - nested `__pycache__/` payload under `mcp_server/semantic_kernel/`
- Generated artifacts outside the deleted legacy package tree:
  - `none_found`

## Protected Historical Exceptions

- path: `../07 - MCP Server/migration/phase14_mcp_cutover.md`
  - matched_pattern: `legacy old tool names and deleted legacy paths`
  - reason: historical cutover note retained by the build plan
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../07 - MCP Server/migration/phase14_legacy_cleanup_inventory.json`
  - matched_pattern: `legacy old paths and symbols`
  - reason: historical legacy inventory retained by the build plan
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../07 - MCP Server/migration/phase15_legacy_unlink_report.md`
  - matched_pattern: `legacy old tool names and deleted legacy paths`
  - reason: historical unlink report retained by the build plan
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../07 - MCP Server/migration/phase15_legacy_state_policy.md`
  - matched_pattern: `legacy state path references`
  - reason: historical state-policy note retained by the build plan
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../07 - MCP Server/migration/phase15_legacy_test_disposition.json`
  - matched_pattern: `legacy old test names and reasons`
  - reason: historical test-disposition note retained by the build plan
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../07 - MCP Server/migration/phase16_legacy_deletion_manifest.json`
  - matched_pattern: `legacy old paths and cleanup reasons`
  - reason: current-phase deletion inventory
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../07 - MCP Server/migration/phase16_legacy_cleanup_report.md`
  - matched_pattern: `legacy old paths, blocker traces and cleanup outcomes`
  - reason: current-phase cleanup evidence
  - owner: `phase16_cleanup`
  - permanent: `true`
- path: `../08 - Semantic Control Kernel/SPEC_Semantic_Control_Kernel_Build.md`
  - matched_pattern: `phase-local legacy cleanup requirements and historical old-kernel references`
  - reason: authoritative build-phase source that defines the deletion boundary and allowed historical references
  - owner: `phase16_cleanup`
  - permanent: `true`

## Dead-Code Scan Results

- Active product/runtime/doc scan roots are clean of:
  - old package imports
  - old catalog and handler file names
  - action-catalog/open-inspect-execute routing names
  - workflow-family follow-up keys
  - old state-path references in active docs
- Old `test_semantic_kernel*` files are removed.
- Old compatibility helper `semantic_kernel_spec_helpers.py` is removed.
- MCP support helpers now emit canonical `safe_next_kernel_tools` and `recommended_first_kernel_tool` guidance instead of workflow-family routing keys.

## Tests Run

- Pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase15_no_old_kernel_imports.py tests\\test_phase15_old_tools_retired.py tests\\test_phase15_registry_unlinked.py tests\\test_phase15_permissions_semantic_control_kernel.py tests\\test_phase15_runtime_manifest_unlinked.py tests\\test_phase15_product_semantics_no_workflow_family_ids.py tests\\test_phase15_state_is_not_runtime_truth.py tests\\test_phase15_non_kernel_tool_regression.py -q`
  - exit status: `0`
  - summary: `12 passed`
- Fail then fixed: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_dead_code_scans.py tests\\test_phase16_import_start_smoke.py tests\\test_phase16_mcp_tool_catalog_snapshot.py tests\\test_phase16_runtime_manifest_clean.py tests\\test_phase16_mcp_regression_subset.py tests\\test_phase16_new_kernel_surface_regression.py tests\\test_phase16_phase14_bridge_regression.py tests\\test_phase16_phase15_unlink_regression.py tests\\test_phase16_state_policy_enforced.py tests\\test_phase16_docs_product_semantics_clean.py tests\\test_phase16_client_frontend_blocker_scan.py -q`
  - exit status: `1`
  - summary: `25 passed, 1 failed`
- Pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_client_frontend_blocker_scan.py tests\\test_phase16_cleanup_artifact_truth.py tests\\test_phase16_state_policy_enforced.py -q`
  - exit status: `0`
  - summary: `5 passed`
- Pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_dead_code_scans.py tests\\test_phase16_import_start_smoke.py tests\\test_phase16_mcp_tool_catalog_snapshot.py tests\\test_phase16_runtime_manifest_clean.py tests\\test_phase16_mcp_regression_subset.py tests\\test_phase16_new_kernel_surface_regression.py tests\\test_phase16_phase14_bridge_regression.py tests\\test_phase16_phase15_unlink_regression.py tests\\test_phase16_state_policy_enforced.py tests\\test_phase16_docs_product_semantics_clean.py tests\\test_phase16_client_frontend_blocker_scan.py tests\\test_phase16_cleanup_artifact_truth.py -q`
  - exit status: `0`
  - summary: `28 passed`
- Crash-prevention audit fail then fixed: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_client_frontend_blocker_scan.py tests\\test_phase16_cleanup_artifact_truth.py -q`
  - exit status: `1`
  - summary: `1 passed, 2 failed`
  - failure: stale Phase 16 Client Frontend blocker report expected old product matches that no longer exist after the Phase 17 rewrite and did not classify negative-test fixtures separately.
- Crash-prevention audit fail then fixed: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_dead_code_scans.py tests\\test_phase16_import_start_smoke.py tests\\test_phase16_mcp_tool_catalog_snapshot.py tests\\test_phase16_runtime_manifest_clean.py tests\\test_phase16_mcp_regression_subset.py tests\\test_phase16_new_kernel_surface_regression.py tests\\test_phase16_phase14_bridge_regression.py tests\\test_phase16_phase15_unlink_regression.py tests\\test_phase16_state_policy_enforced.py tests\\test_phase16_docs_product_semantics_clean.py tests\\test_phase16_client_frontend_blocker_scan.py tests\\test_phase16_cleanup_artifact_truth.py -q`
  - exit status: `1`
  - summary: `27 passed, 1 failed`
  - failure: Phase 16 Phase 14 wrapper called the old event-scoped recovery test signature and skipped the current monkeypatch fixture contract.
- Crash-prevention audit pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_phase14_bridge_regression.py -q`
  - exit status: `0`
  - summary: `5 passed`
- Crash-prevention audit pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_dead_code_scans.py tests\\test_phase16_import_start_smoke.py tests\\test_phase16_mcp_tool_catalog_snapshot.py tests\\test_phase16_runtime_manifest_clean.py tests\\test_phase16_mcp_regression_subset.py tests\\test_phase16_new_kernel_surface_regression.py tests\\test_phase16_phase14_bridge_regression.py tests\\test_phase16_phase15_unlink_regression.py tests\\test_phase16_state_policy_enforced.py tests\\test_phase16_docs_product_semantics_clean.py tests\\test_phase16_client_frontend_blocker_scan.py tests\\test_phase16_cleanup_artifact_truth.py -q`
  - exit status: `0`
  - summary: `28 passed`
- Crash-prevention audit Phase 15 gate rerun: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase15_no_old_kernel_imports.py tests\\test_phase15_old_tools_retired.py tests\\test_phase15_registry_unlinked.py tests\\test_phase15_permissions_semantic_control_kernel.py tests\\test_phase15_runtime_manifest_unlinked.py tests\\test_phase15_product_semantics_no_workflow_family_ids.py tests\\test_phase15_state_is_not_runtime_truth.py tests\\test_phase15_non_kernel_tool_regression.py -q`
  - exit status: `0`
  - summary: `12 passed`
- Crash-prevention audit docs/spec drift pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_docs_product_semantics_clean.py tests\\test_phase16_cleanup_artifact_truth.py -q`
  - exit status: `0`
  - summary: `4 passed`
- Crash-prevention audit final Phase 16 pass: `dev-tests\\.venv\\Scripts\\pytest.exe tests\\test_phase16_dead_code_scans.py tests\\test_phase16_import_start_smoke.py tests\\test_phase16_mcp_tool_catalog_snapshot.py tests\\test_phase16_runtime_manifest_clean.py tests\\test_phase16_mcp_regression_subset.py tests\\test_phase16_new_kernel_surface_regression.py tests\\test_phase16_phase14_bridge_regression.py tests\\test_phase16_phase15_unlink_regression.py tests\\test_phase16_state_policy_enforced.py tests\\test_phase16_docs_product_semantics_clean.py tests\\test_phase16_client_frontend_blocker_scan.py tests\\test_phase16_cleanup_artifact_truth.py -q`
  - exit status: `0`
  - summary: `29 passed`

## Residual Risks

- none

## Phase 17 Blockers

- none

## Client Frontend Negative Test Fixtures

- owner: `phase17_client_frontend`
- Current Client Frontend product files are clean of old action-catalog routing strings. Remaining matches are Phase 17 negative tests that assert forbidden-pattern fixtures do not leak into active Agent prompts, tool lists or workflow calls.
- `dev-tests/tests/pipeline-agent-legacy-surface-rejection.test.js`
  - matched_patterns: `llm_action_catalog`, `open_workflow`, `inspect_workflow`, `execute_.*workflow_action`, `workflow_family_id`, `pipeline_action`, `action_token`
- `dev-tests/tests/pipeline-agent-tool-surface.test.js`
  - matched_patterns: `pipeline_action`
- `dev-tests/tests/pipeline-agent-workflow.test.js`
  - matched_patterns: `llm_action_catalog`, `open_workflow`, `inspect_workflow`, `pipeline_action`
- `dev-tests/tests/pipeline-agent-workflow-prompt.test.js`
  - matched_patterns: `llm_action_catalog`, `open_workflow`, `inspect_workflow`, `pipeline_action`
- `dev-tests/tests/pipeline-agent-workflow-status.test.js`
  - matched_patterns: `inspect_workflow`
