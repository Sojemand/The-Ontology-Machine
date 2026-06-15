from __future__ import annotations

from orchestrator.edit_contract.summary import build_module_summary


def test_build_module_summary_describes_policy_only_scope_and_surfaces() -> None:
    summary = build_module_summary()

    assert summary.startswith("ORCHESTRATOR POLICY HELP")
    assert "The Orchestrator remains run- and debug-owned." in summary
    assert "This edit_contract externalizes only non-GUI owner-local policy defaults." in summary
    assert "Summary also adds four snapshot cards" in summary
    assert "Each policy surface uses top-level groups" in summary
    assert "Route Intake Policy Guide" in summary
    assert "Artifact Publication Policy Guide" in summary
    assert "`state/ui_state.json`, `state/runtime_settings.json`, credentials, and protocol constants remain out of scope." in summary
    assert "Recommended First-Time Workflow" in summary
