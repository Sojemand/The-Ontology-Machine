from __future__ import annotations

from typing import Any

from .paths import MODULE_ROOT, PHASE19_REQUIRED_KERNEL_TESTS, _json_file


def _blocking_issues(
    dead_code_matches: list[dict[str, str]],
    *,
    command_records: list[dict[str, Any]],
    scaffold_only: bool,
    tool_surface_contracts: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    missing_phase19 = [path.name for path in PHASE19_REQUIRED_KERNEL_TESTS if not path.exists()]
    if missing_phase19:
        issues.append(
            {
                "anchor": "missing-phase19-kernel-tests",
                "owner": "phase19",
                "path": "08 - Semantic Control Kernel/dev-tests/tests/",
                "reason": "Required Phase 19 Kernel regression tests are missing from the worktree.",
                "next_action": "Restore or implement the three Phase 19 Kernel suites before a real go-live attempt.",
                "details": ", ".join(missing_phase19),
            }
        )
    module_manifest = _json_file(MODULE_ROOT / "module-manifest.json")
    runtime_manifest = _json_file(MODULE_ROOT / "runtime" / "runtime-manifest.json")
    if (
        module_manifest.get("status") != runtime_manifest.get("status")
        or module_manifest.get("contract_version") != runtime_manifest.get("contract_version")
    ):
        issues.append(
            {
                "anchor": "runtime-contract-drift",
                "owner": "phase1_runtime_contract",
                "path": "08 - Semantic Control Kernel/module-manifest.json",
                "reason": "Module manifest and runtime manifest still advertise different status contracts.",
                "next_action": "Reconcile the runtime preflight contract with the current public module surface before a release run.",
                "details": (
                    f"module={module_manifest.get('status')} runtime={runtime_manifest.get('status')} "
                    f"module_contract={module_manifest.get('contract_version')} runtime_contract={runtime_manifest.get('contract_version')}"
                ),
            }
        )
    if dead_code_matches:
        issues.append(
            {
                "anchor": "active-dead-code-matches",
                "owner": "phase20_cleanup",
                "path": "release/go_live/<run_id>/dead_code_scan_report.md",
                "reason": "Forbidden old-Kernel patterns remain in active product roots.",
                "next_action": "Remove or rewrite the active matches so the Phase 20 dead-code scan returns clean.",
                "details": f"{len(dead_code_matches)} active match(es)",
            }
        )
    parity = dict(tool_surface_contracts.get("parity") or {})
    if not all(bool(value) for value in parity.values()):
        drifted = ", ".join(sorted(name for name, value in parity.items() if not value))
        issues.append(
            {
                "anchor": "surface-contract-drift",
                "owner": "phase20_surface",
                "path": "release/go_live/<run_id>/mcp_public_agent_snapshot.json",
                "reason": "Kernel, MCP Server and Client Frontend tool surfaces are not aligned on one truth.",
                "next_action": "Reconcile the MCP visibility contract, Kernel surface inventory and Client Frontend tool arrays before go-live.",
                "details": drifted,
            }
        )
    for record in command_records:
        if record["result"] == "pass":
            continue
        issues.append(
            {
                "anchor": str(record["blocking_issue_anchor"]),
                "owner": str(record["module_key"]),
                "path": str(record["log_path"]),
                "reason": "A required Phase 20 regression command did not pass.",
                "next_action": "Inspect the linked command log, fix the underlying failing check, and rerun the go-live bundle.",
                "details": (
                    f"command={record['command']} exit={record['exit_code']} result={record['result']} "
                    f"scope={record['expected_test_scope']}"
                ),
            }
        )
    if scaffold_only:
        issues.append(
            {
                "anchor": "full-regression-matrix-pending",
                "owner": "phase20_go_live",
                "path": "08 - Semantic Control Kernel/release/go_live/",
                "reason": "The bundle was generated in scaffold-only mode and does not contain a real command execution matrix.",
                "next_action": "Run the generator without --scaffold-only to execute the full regression matrix.",
                "details": "All required commands are cataloged, but no live execution was attempted.",
            }
        )
    return issues
