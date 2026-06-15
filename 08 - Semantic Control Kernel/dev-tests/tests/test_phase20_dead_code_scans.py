from __future__ import annotations

import sys
from pathlib import Path

from phase20_go_live_support import latest_go_live_dir


MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from tools.generate_go_live_bundle import _scan_forbidden_matches  # noqa: E402


def test_active_roots_are_clean_of_forbidden_old_kernel_patterns() -> None:
    assert _scan_forbidden_matches() == []


def test_dead_code_scan_report_records_clean_state() -> None:
    report = (latest_go_live_dir() / "dead_code_scan_report.md").read_text(encoding="utf-8")

    assert "`active_match_count`: `0`" in report
    assert "none" in report

