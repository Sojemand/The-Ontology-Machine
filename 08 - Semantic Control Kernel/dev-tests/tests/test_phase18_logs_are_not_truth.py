from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.debug.log_truth_policy import canonical_truth_required


MODULE_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = MODULE_ROOT / "dev-tests" / "fixtures" / "phase18" / "log_truth_boundary" / "fixture.json"
SOURCE_ROOT = MODULE_ROOT / "semantic_control_kernel"
FORBIDDEN_TRUTH_TOKENS = (
    "state/debug/",
    "state/support/bundles/",
    "trace_links.json",
    "redaction_report.json",
)


def test_debug_evidence_does_not_replace_missing_canonical_truth() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    decision = canonical_truth_required(**fixture)

    assert decision["decision"] == "blocked"
    assert decision["used_debug_evidence"] is True
    assert decision["reason"] == "canonical_truth_missing"


def test_runtime_paths_do_not_read_debug_or_support_bundle_state_as_truth() -> None:
    scanned_files: list[Path] = []
    for root_name in ("policy", "domain", "workflows", "services", "surface", "state_resolution"):
        root = SOURCE_ROOT / root_name
        for path in root.rglob("*.py"):
            scanned_files.append(path)
            text = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_TRUTH_TOKENS:
                assert token not in text, f"{path} must not treat debug/support artifacts as workflow truth."

    assert scanned_files
