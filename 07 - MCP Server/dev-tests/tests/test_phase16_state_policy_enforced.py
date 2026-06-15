from __future__ import annotations

from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
STATE_POLICY_PATH = MODULE_ROOT / "migration" / "phase15_legacy_state_policy.md"
CLEANUP_REPORT_PATH = MODULE_ROOT / "migration" / "phase16_legacy_cleanup_report.md"
LEGACY_STATE_ROOT = MODULE_ROOT / "state" / "semantic_kernel"


def test_phase16_does_not_require_legacy_state_as_historical_fixture() -> None:
    text = STATE_POLICY_PATH.read_text(encoding="utf-8").casefold()

    assert "removed" in text
    assert "no longer expected" in text
    assert not LEGACY_STATE_ROOT.exists()


def test_cleanup_report_records_the_exact_state_handling_decision() -> None:
    report = CLEANUP_REPORT_PATH.read_text(encoding="utf-8").casefold()
    assert "state handling" in report
    assert "removed" in report
    assert "no test or runtime path" in report
