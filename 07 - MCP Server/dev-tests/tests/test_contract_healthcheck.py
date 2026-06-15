from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.contract_client import ContractError, _load_response
from mcp_server.orchestrator_contract import main
from mcp_server.runtime_preflight import check_runtime_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_UNLINKED_REQUIRED_FILES = {
    "mcp_server/tool_catalog_semantic_kernel.py",
    "mcp_server/tool_handlers_semantic_kernel.py",
}


def test_healthcheck_contract_writes_response(tmp_path) -> None:
    response_path = tmp_path / "response.json"

    assert main(["--response", str(response_path)]) == 0

    payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["healthy"] is True
    assert payload["tool_count"] > 0
    assert payload["runtime"]["ok"] is True


def test_runtime_manifest_preflight_reports_required_files() -> None:
    payload = check_runtime_manifest()

    assert payload["ok"] is True
    assert payload["missing_required_files"] == []
    assert payload["manifest_path"].endswith("runtime-manifest.json")


def test_contract_response_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="Contract-Response fehlt"):
        _load_response(tmp_path / "missing-response.json")


def test_contract_response_non_object_fails_closed(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    response_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ContractError, match="JSON-Objekt"):
        _load_response(response_path)


def test_runtime_manifest_lists_all_product_python_sources() -> None:
    manifest = json.loads((PROJECT_ROOT / "runtime" / "runtime-manifest.json").read_text(encoding="utf-8"))
    required = {str(item).replace("\\", "/") for item in manifest["required_files"]}
    product_sources = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        for path in (PROJECT_ROOT / "mcp_server").rglob("*.py")
        if "__pycache__" not in path.parts
        if not _is_phase15_unlinked_source(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
    }

    assert sorted(product_sources - required) == []
    assert "mcp_server/tool_catalog_semantic_control_kernel.py" in required
    assert "mcp_server/tool_handlers_semantic_control_kernel.py" in required
    assert "mcp_server/tool_visibility.py" in required
    assert LEGACY_UNLINKED_REQUIRED_FILES.isdisjoint(required)
    assert not any(path.startswith("mcp_server/semantic_kernel/") for path in required)


def _is_phase15_unlinked_source(relative: str) -> bool:
    return relative.startswith("mcp_server/semantic_kernel/") or relative in LEGACY_UNLINKED_REQUIRED_FILES
