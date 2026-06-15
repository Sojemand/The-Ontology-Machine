from __future__ import annotations

import sys
from pathlib import Path

from phase20_go_live_support import latest_go_live_dir, load_json


MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from semantic_control_kernel.surface.agent_tools import PERMANENT_AGENT_TOOL_DEFINITIONS  # noqa: E402


def test_e2e_matrix_covers_all_permanent_agent_tools() -> None:
    root = latest_go_live_dir()
    payload = load_json(root / "e2e_matrix" / "e2e_fixture_matrix.json")
    expected = [definition.tool_name for definition in PERMANENT_AGENT_TOOL_DEFINITIONS]

    assert payload["permanent_tool_coverage"] == expected
    assert len(payload["entries"]) >= 10


def test_realistic_corpus_manifest_meets_phase20_requirements() -> None:
    root = latest_go_live_dir()
    payload = load_json(root / "e2e_matrix" / "e2e_fixture_matrix.json")
    fixture_root = MODULE_ROOT / str(payload["realistic_corpus_path"])
    manifest = load_json(fixture_root / "fixture_manifest.json")

    assert manifest["source_document_count"] >= 5
    assert len(manifest["document_classes"]) >= 2
    assert "scan_vision" in manifest["normalized_histories"]
    assert "born_digital_file" in manifest["normalized_histories"]
    assert manifest["has_multi_page_source"] is True
    assert manifest["has_table_like_source"] is True
    assert manifest["has_ambiguous_semantic_coverage"] is True
    assert manifest["prohibited_secret_scan_results"] == []
    assert (fixture_root / "README.md").is_file()
    assert len(manifest["files"]) >= 10
