from __future__ import annotations

from validator_vision.edit_contract.summary import build_module_summary


def test_build_module_summary_describes_checks_match_and_report_policy() -> None:
    summary = build_module_summary()

    assert summary.startswith("VALIDATOR HELP")
    assert "How To Read This Slot" in summary
    assert "Checks Guide" in summary
    assert "Match Guide" in summary
    assert "`match.row_anchor_keys` defines the saved anchor keys used to align row-level evidence across payloads." in summary
    assert "Prompts/Assets stays intentionally empty for this module" in summary
    assert "Report Preview Guide" in summary
    assert "Recommended First-Time Workflow" in summary
