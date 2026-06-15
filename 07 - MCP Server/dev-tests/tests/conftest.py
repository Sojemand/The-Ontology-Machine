from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest

from mcp_server import permissions
from mcp_server.tool_visibility import kernel_syscall_context

MODULE_ROOT = Path(__file__).resolve().parents[2]
IGNORE_DISPOSITIONS = {"replace_with_new_phase14_or_phase15_test", "delete_in_phase_16"}


@pytest.fixture(autouse=True)
def elevated_agent_level_for_tool_tests(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    policy_path = tmp_path / "config" / "agent_permissions.json"
    monkeypatch.setattr(permissions, "POLICY_PATH", policy_path)
    monkeypatch.setenv("VISION_MCP_CONTRACT_CALLS_DIR", str(tmp_path / "mcp_contract_calls"))
    monkeypatch.setenv("VISION_MCP_AGENT_LEVEL", "L3_ADMIN")
    with kernel_syscall_context():
        yield


def pytest_ignore_collect(collection_path, path=None, config=None) -> bool:  # pragma: no cover - pytest hook
    candidate = Path(str(collection_path))
    return candidate.name in _ignored_legacy_tests()


@lru_cache(maxsize=1)
def _ignored_legacy_tests() -> set[str]:
    payload = json.loads((MODULE_ROOT / "migration" / "phase15_legacy_test_disposition.json").read_text(encoding="utf-8"))
    return {
        Path(str(entry["path"])).name
        for entry in payload["entries"]
        if str(entry["disposition"]) in IGNORE_DISPOSITIONS
    }

