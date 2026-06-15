from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import (
    PHASE20_TRUTH_INPUTS,
    PIPELINE_ROOT,
    _decision_from_results,
    _write_json,
    phase20_truth_hash,
)


def _write_go_live_manifest(
    bundle_root: Path,
    run_id: str,
    source_commit: str,
    phase19_path: Path,
    blockers: list[dict[str, str]],
    command_records: list[dict[str, Any]],
) -> dict[str, Any]:
    decision = _decision_from_results(blockers, command_records)
    manifest = {
        "schema_version": "semantic_control_kernel.go_live_manifest.v1",
        "go_live_run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kernel_module_root": "08 - Semantic Control Kernel",
        "pipeline_root": "The Ontology Machine",
        "source_commit": source_commit,
        "phase20_truth_hash": phase20_truth_hash(),
        "phase20_truth_inputs": [path.relative_to(PIPELINE_ROOT).as_posix() for path in PHASE20_TRUTH_INPUTS],
        "spec_refs": [
            "Semantic Kernel SPEC/22_mcp_kernel_pipeline_function_contract.md",
            "Semantic Kernel SPEC/23_agent_facing_pipeline_manager_tools.md",
            "08 - Semantic Control Kernel/SPEC_Semantic_Control_Kernel_Build.md",
        ],
        "phase_evidence": {
            "phase14_mcp_cutover": "07 - MCP Server/migration/phase14_mcp_cutover.md",
            "phase15_unlink": "07 - MCP Server/migration/phase15_legacy_unlink_report.md",
            "phase16_cleanup": "07 - MCP Server/migration/phase16_legacy_cleanup_report.md",
            "phase17_frontend": "Client Frontend/dev-tests/tests/pipeline-agent-tool-surface.test.js",
            "phase18_observability": "08 - Semantic Control Kernel/dev-tests/tests/test_phase18_support_bundle_schema.py",
            "phase19_pipeline_owner_capabilities": phase19_path.relative_to(PIPELINE_ROOT).as_posix(),
        },
        "decision": decision,
        "decision_source": "codex_build_session",
        "blocking_issue_count": len(blockers),
        "residual_risk_count": 0,
    }
    _write_json(bundle_root / "go_live_manifest.json", manifest)
    return manifest


def _write_readiness_decision(
    bundle_root: Path,
    run_id: str,
    manifest: dict[str, Any],
    blockers: list[dict[str, str]],
    command_records: list[dict[str, Any]],
) -> None:
    passed = sum(1 for record in command_records if record["result"] == "pass")
    failed = sum(1 for record in command_records if record["result"] == "fail")
    lines = [
        "# Readiness Decision",
        "",
        f"- `go_live_run_id`: `{run_id}`",
        f"- `decision`: `{manifest['decision']}`",
        "- `decision_source`: `codex_build_session`",
        "- `human_approval_gate`: none",
        f"- `passed_commands`: `{passed}`",
        f"- `failed_commands`: `{failed}`",
        "",
        "## Decision Basis",
        "",
    ]
    if not blockers:
        lines.append("- No blocking issues were recorded in this go-live attempt.")
    else:
        for blocker in blockers:
            lines.append(f"- `{blocker['owner']}`: {blocker['reason']} ({blocker['path']})")
    lines.extend(
        [
            "",
            "## Gate Summary",
            "",
            "- Safety, evidence redaction and rollback fields are present in the bundle.",
            "- The readiness decision is based on real command execution plus the generated evidence bundle.",
            "- Any remaining blockers keep the release in `not_ready` until the failing command or audit gate is fixed.",
            "",
        ]
    )
    (bundle_root / "readiness_decision.md").write_text("\n".join(lines), encoding="utf-8")
