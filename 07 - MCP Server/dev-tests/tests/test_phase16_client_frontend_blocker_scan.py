from __future__ import annotations

import re
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
CLIENT_FRONTEND_ROOT = PIPELINE_ROOT / "Client Frontend"
CLEANUP_REPORT_PATH = MODULE_ROOT / "migration" / "phase16_legacy_cleanup_report.md"
SCAN_ROOTS = (
    CLIENT_FRONTEND_ROOT / "client_frontend",
    CLIENT_FRONTEND_ROOT / "server",
    CLIENT_FRONTEND_ROOT / "src",
    CLIENT_FRONTEND_ROOT / "dev-tests" / "tests",
    CLIENT_FRONTEND_ROOT / "README.md",
)
TEXT_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".json", ".md"}
BLOCKER_PATTERNS = (
    r"llm_action_catalog",
    r"open_workflow",
    r"inspect_workflow",
    r"execute_.*workflow_action",
    r"workflow_family_id",
    r"pipeline_action",
    r"action_token",
)
ALLOWED_NEGATIVE_FIXTURE_PATHS = {
    "dev-tests/tests/pipeline-agent-legacy-surface-rejection.test.js",
    "dev-tests/tests/pipeline-agent-tool-surface.test.js",
    "dev-tests/tests/pipeline-agent-workflow-prompt.test.js",
    "dev-tests/tests/pipeline-agent-workflow-status.test.js",
    "dev-tests/tests/pipeline-agent-workflow.test.js",
}


def test_frontend_blockers_are_scanned_and_recorded_for_phase17() -> None:
    matches = _scan_blockers()
    negative_fixtures = _scan_negative_fixtures()
    report = CLEANUP_REPORT_PATH.read_text(encoding="utf-8")
    blocker_section = _section(report, "Phase 17 Blockers")
    fixture_section = _section(report, "Client Frontend Negative Test Fixtures")

    assert "Phase 17 Blockers" in report
    if not matches:
        assert "none" in blocker_section.casefold()
    else:
        reported_paths = {
            line.split("`")[1]
            for line in blocker_section.splitlines()
            if line.strip().startswith("- `")
        }
        assert reported_paths == set(matches)
        for relative_path, patterns in matches.items():
            assert relative_path in blocker_section
            for pattern in patterns:
                assert pattern in blocker_section
        assert "phase17_client_frontend" in blocker_section

    for relative_path, patterns in negative_fixtures.items():
        assert relative_path in fixture_section
        for pattern in patterns:
            assert pattern in fixture_section
    assert "forbidden-pattern fixtures" in fixture_section


def _scan_blockers() -> dict[str, list[str]]:
    return {
        path: patterns
        for path, patterns in _scan_all_matches().items()
        if path not in ALLOWED_NEGATIVE_FIXTURE_PATHS
    }


def _scan_negative_fixtures() -> dict[str, list[str]]:
    return {
        path: patterns
        for path, patterns in _scan_all_matches().items()
        if path in ALLOWED_NEGATIVE_FIXTURE_PATHS
    }


def _scan_all_matches() -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            matched = [pattern for pattern in BLOCKER_PATTERNS if re.search(pattern, text)]
            if matched:
                hits[path.relative_to(CLIENT_FRONTEND_ROOT).as_posix()] = matched
    return hits


def _section(report: str, heading: str) -> str:
    marker = f"## {heading}"
    start = report.index(marker)
    next_heading = report.find("\n## ", start + len(marker))
    if next_heading == -1:
        return report[start:]
    return report[start:next_heading]
