from __future__ import annotations

from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
README_PATH = MODULE_ROOT / "README.md"
STATE_README_PATH = MODULE_ROOT / "state" / "README.md"


def test_operations_readmes_contain_required_phase18_sections() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    state_readme = STATE_README_PATH.read_text(encoding="utf-8")

    for heading in (
        "Operations And Support",
        "Runtime State Locations",
        "Trace And Progress Correlation",
        "Support Bundle Inspection",
        "Redaction Guarantees",
        "Common Blockers And Recovery Evidence",
        "Runtime Check And Test Commands",
        "Cleanup And Retention",
        "Logs Are Not Workflow Truth",
    ):
        assert heading in readme

    for token in (
        "state/debug/traces/",
        "state/debug/adapter_calls/",
        "state/debug/llm_attempts/",
        "state/debug/redaction_reports/",
        "state/support/index.json",
        "state/support/bundles/",
        "state/support/cleanup_history/",
    ):
        assert token in state_readme
