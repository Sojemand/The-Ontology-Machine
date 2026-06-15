from __future__ import annotations

import json
from pathlib import Path

from . import test_phase16_client_frontend_blocker_scan as phase17_blockers


MODULE_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = MODULE_ROOT / "migration" / "phase16_legacy_deletion_manifest.json"
REPORT_PATH = MODULE_ROOT / "migration" / "phase16_legacy_cleanup_report.md"
EXPECTED_PROTECTED_EXCEPTION_PATHS = {
    "../07 - MCP Server/migration/phase14_mcp_cutover.md",
    "../07 - MCP Server/migration/phase14_legacy_cleanup_inventory.json",
    "../07 - MCP Server/migration/phase15_legacy_unlink_report.md",
    "../07 - MCP Server/migration/phase15_legacy_state_policy.md",
    "../07 - MCP Server/migration/phase15_legacy_test_disposition.json",
    "../07 - MCP Server/migration/phase16_legacy_deletion_manifest.json",
    "../07 - MCP Server/migration/phase16_legacy_cleanup_report.md",
    "../08 - Semantic Control Kernel/SPEC_Semantic_Control_Kernel_Build.md",
}


def test_deletion_manifest_records_state_removal_and_all_protected_exceptions() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    protected = {str(item["path"]): item for item in payload["protected_exceptions"]}

    assert payload["schema_version"] == "mcp.phase16_legacy_deletion_manifest.v1"
    assert EXPECTED_PROTECTED_EXCEPTION_PATHS <= set(protected)
    assert any(
        item["path"] == "../07 - MCP Server/state/semantic_kernel/"
        and item["policy"] == "removed"
        and item["active_runtime_truth"] is False
        for item in payload["state_paths"]
    )
    for item in protected.values():
        assert str(item["matched_pattern"]).strip()
        assert str(item["reason"]).strip()
        assert str(item["owner"]).strip() == "phase16_cleanup"
        assert isinstance(item["permanent"], bool)


def test_cleanup_report_matches_manifest_exceptions_and_frontend_residual_risk() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    report = REPORT_PATH.read_text(encoding="utf-8")
    protected_section = phase17_blockers._section(report, "Protected Historical Exceptions")
    residual_section = phase17_blockers._section(report, "Residual Risks")
    blocker_section = phase17_blockers._section(report, "Phase 17 Blockers")
    fixture_section = phase17_blockers._section(report, "Client Frontend Negative Test Fixtures")
    blockers = phase17_blockers._scan_blockers()
    negative_fixtures = phase17_blockers._scan_negative_fixtures()

    for item in payload["protected_exceptions"]:
        assert str(item["path"]) in protected_section
        assert str(item["matched_pattern"]) in protected_section
        assert str(item["owner"]) in protected_section

    if not blockers:
        assert "none" in residual_section.casefold()
        assert "none" in blocker_section.casefold()
    else:
        assert "none" not in residual_section.casefold()
        assert "phase17_client_frontend" in residual_section
        for relative_path, patterns in blockers.items():
            assert relative_path in residual_section
            assert relative_path in blocker_section
            for pattern in patterns:
                assert pattern in blocker_section

    for relative_path, patterns in negative_fixtures.items():
        assert relative_path in fixture_section
        for pattern in patterns:
            assert pattern in fixture_section
