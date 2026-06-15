from __future__ import annotations

from phase20_go_live_support import latest_go_live_dir, load_json


def test_readiness_decision_is_codex_owned_and_references_rollback() -> None:
    root = latest_go_live_dir()
    manifest = load_json(root / "go_live_manifest.json")
    decision = (root / "readiness_decision.md").read_text(encoding="utf-8")
    rollback = (root / "rollback_drill.md").read_text(encoding="utf-8")

    assert manifest["decision_source"] == "codex_build_session"
    assert "human_approval_checklist" not in manifest
    assert f"`decision`: `{manifest['decision']}`" in decision
    assert "`rollback_source_ref`:" in rollback
    assert "old_agent_surface_not_target_architecture" in rollback


def test_readiness_decision_is_consistent_with_blockers_and_risks() -> None:
    root = latest_go_live_dir()
    manifest = load_json(root / "go_live_manifest.json")
    blockers = (root / "blocking_issues.md").read_text(encoding="utf-8")
    risks = (root / "residual_risks.md").read_text(encoding="utf-8")

    if manifest["decision"] == "not_ready":
        assert manifest["blocking_issue_count"] >= 1
        assert "none" not in blockers.lower()
    if manifest["decision"] == "ready":
        assert manifest["blocking_issue_count"] == 0
        assert risks.strip().endswith("none")
