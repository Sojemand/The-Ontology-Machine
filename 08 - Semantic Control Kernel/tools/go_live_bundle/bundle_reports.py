from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bundle_manifest_reports import _write_go_live_manifest, _write_readiness_decision
from .paths import _write_json, phase20_truth_hash


def _write_dead_code_report(bundle_root: Path, run_id: str, matches: list[dict[str, str]]) -> None:
    lines = [
        "# Dead Code Scan Report",
        "",
        f"- `go_live_run_id`: `{run_id}`",
        f"- `active_match_count`: `{len(matches)}`",
        "",
    ]
    if not matches:
        lines.append("none")
    else:
        for match in matches:
            lines.extend(
                [
                    f"## {match['path']}:{match['line']}",
                    "",
                    f"- `matched_pattern`: `{match['matched_pattern']}`",
                    "- `reason`: active product root still contains a forbidden old-Kernel pattern",
                    "- `owner`: phase20_cleanup",
                    "- `historical_or_negative_test`: false",
                    f"- `snippet`: `{match['snippet']}`",
                    "",
                ]
            )
    (bundle_root / "dead_code_scan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_worktree_manifest(bundle_root: Path, run_id: str, source_commit: str, worktree_status: str) -> None:
    contents = [
        f"go_live_run_id={run_id}",
        f"generated_at={datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        f"source_commit={source_commit}",
        f"phase20_truth_hash={phase20_truth_hash()}",
        "",
        worktree_status.strip() or "clean",
        "",
    ]
    (bundle_root / "worktree_manifest.txt").write_text("\n".join(contents), encoding="utf-8")


def _write_docs_summary(bundle_root: Path, run_id: str, blockers: list[dict[str, str]]) -> None:
    lines = [
        "# Documentation Diff Summary",
        "",
        f"- `go_live_run_id`: `{run_id}`",
        "- Updated Kernel README to describe the active workflow, adapter and release-evidence boundary.",
        "- Added Normalizer to the Kernel external dependency list in `module-manifest.json`.",
        "- Reworded Client Frontend retired-surface guidance to avoid reintroducing forbidden public names in active docs.",
        "- Dead-code cleanup replaced literal retired-name lists with generated equivalents where the active surface still needs fail-closed checks.",
        f"- Blocking issue count in this go-live attempt: `{len(blockers)}`.",
        "",
    ]
    (bundle_root / "documentation_diff_summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_rollback_drill(bundle_root: Path, run_id: str, rollback_source_ref: str) -> None:
    lines = [
        "# Rollback Drill",
        "",
        f"- `rollback_source_ref`: `{rollback_source_ref}`",
        f"- `created_at`: `{datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}`",
        "- `created_by`: `codex_build_session`",
        "- `restore_scope`: `Restore the last stable MCP and Client Frontend tree from the named git commit before re-running the release matrix.`",
        "- `expected_user_impact`: `Temporary loss of the current Semantic Control Kernel cutover candidate while the previous stable bridge is restored.`",
        "- `data_preservation_notes`: `Do not keep retired old-Kernel source files in the active tree; preserve only committed owner data and external user workspaces.`",
        "- `commands_or_manual_steps`: `git checkout <rollback_source_ref>; rebuild runtimes; restart MCP Server and Client Frontend with the restored tree.`",
        "- `verification_commands`: `run-dev-tests.bat --module \"07 - MCP Server\" --run-only` and `run-dev-tests.bat --module \"Client Frontend\" --run-only` must pass against the restored commit.",
        "- `forward_fix_return_path`: `Return to the current branch, fix the recorded blockers, rerun the full Phase 20 matrix and generate a new go-live bundle.`",
        "- `old_agent_surface_not_target_architecture`: `Rollback is an operational fallback only; the retired catalog-driven surface is not the future architecture.`",
        "",
    ]
    (bundle_root / "rollback_drill.md").write_text("\n".join(lines), encoding="utf-8")


def _write_blockers(bundle_root: Path, blockers: list[dict[str, str]]) -> None:
    lines = ["# Blocking Issues", ""]
    if not blockers:
        lines.append("none")
    for blocker in blockers:
        lines.extend(
            [
                f"## {blocker['anchor'].replace('-', ' ').title()}",
                "",
                f"- `owner`: `{blocker['owner']}`",
                f"- `path`: `{blocker['path']}`",
                f"- `reason`: {blocker['reason']}",
                f"- `required_follow_up`: {blocker['next_action']}",
                f"- `details`: {blocker['details']}",
                "",
            ]
        )
    (bundle_root / "blocking_issues.md").write_text("\n".join(lines), encoding="utf-8")


def _write_residual_risks(bundle_root: Path) -> None:
    (bundle_root / "residual_risks.md").write_text("# Residual Risks\n\nnone\n", encoding="utf-8")


def _write_test_summary(bundle_root: Path, run_id: str, blockers: list[dict[str, str]], command_records: list[dict[str, Any]]) -> None:
    command_count = len(command_records)
    passed = sum(1 for record in command_records if record["result"] == "pass")
    failed = sum(1 for record in command_records if record["result"] == "fail")
    blocked = sum(1 for record in command_records if record["result"] == "blocked")
    _write_json(
        bundle_root / "test_summary.json",
        {
            "schema_version": "semantic_control_kernel.phase20.test_summary.v1",
            "go_live_run_id": run_id,
            "command_count": command_count,
            "passed_commands": passed,
            "failed_commands": failed,
            "blocked_commands": blocked,
            "blocking_issue_count": len(blockers),
        },
    )


def _write_readme_markers(bundle_root: Path) -> None:
    for directory_name in ("commands", "snapshots", "redaction_checks"):
        marker = bundle_root / directory_name / ".gitkeep"
        marker.write_text("", encoding="utf-8")
