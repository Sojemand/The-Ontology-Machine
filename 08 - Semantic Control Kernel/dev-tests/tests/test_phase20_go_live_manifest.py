from __future__ import annotations

from pathlib import Path

from phase20_go_live_support import latest_go_live_dir, load_json, phase20_truth_hash


REQUIRED_FILES = (
    "go_live_manifest.json",
    "readiness_decision.md",
    "blocking_issues.md",
    "residual_risks.md",
    "rollback_drill.md",
    "command_matrix.md",
    "test_summary.json",
    "phase19_owner_capability_evidence.json",
    "mcp_public_agent_snapshot.json",
    "mcp_kernel_internal_contract_snapshot.json",
    "mcp_continuation_scope_snapshot.json",
    "agent_tool_list_snapshot.json",
    "client_frontend_event_snapshot.json",
    "runtime_manifest_snapshot.json",
    "dead_code_scan_report.md",
    "support_bundle_sample_manifest.json",
    "documentation_diff_summary.md",
    "worktree_manifest.txt",
)

REQUIRED_DIRS = ("commands", "e2e_matrix", "snapshots", "redaction_checks")


def test_go_live_bundle_contains_required_files_and_directories() -> None:
    root = latest_go_live_dir()

    for relative in REQUIRED_FILES:
        assert (root / relative).is_file(), relative
    for relative in REQUIRED_DIRS:
        assert (root / relative).is_dir(), relative


def test_go_live_manifest_matches_run_id_and_schema() -> None:
    root = latest_go_live_dir()
    manifest = load_json(root / "go_live_manifest.json")

    assert manifest["schema_version"] == "semantic_control_kernel.go_live_manifest.v1"
    assert manifest["go_live_run_id"] == root.name
    assert str(manifest["generated_at"]).endswith("Z")
    assert manifest["kernel_module_root"] == "08 - Semantic Control Kernel"
    assert manifest["pipeline_root"] == "The Ontology Machine"
    assert manifest["decision_source"] == "codex_build_session"
    assert manifest["decision"] in {"ready", "ready_with_exceptions", "not_ready"}
    assert manifest["phase20_truth_hash"] == phase20_truth_hash()
    assert manifest["phase20_truth_inputs"]
    assert "human_approval_checklist" not in manifest


def test_worktree_manifest_carries_run_id_and_source_commit_marker() -> None:
    root = latest_go_live_dir()
    text = (root / "worktree_manifest.txt").read_text(encoding="utf-8")

    assert f"go_live_run_id={root.name}" in text
    assert "source_commit=" in text
    assert f"phase20_truth_hash={phase20_truth_hash()}" in text
