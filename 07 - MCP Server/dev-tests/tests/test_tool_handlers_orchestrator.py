from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("orchestrator.healthcheck", {"unexpected": True}, "orchestrator.healthcheck akzeptiert keine Argumente"),
        ("orchestrator.reset", {"ui_state": {}}, "orchestrator.reset akzeptiert keine Argumente"),
    ],
)
def test_orchestrator_atom_tools_reject_arguments(
    tool_name: str, arguments: dict[str, Any], message: str
) -> None:
    with pytest.raises(ToolFailure, match=message):
        call_tool(tool_name, arguments)


def test_orchestrator_healthcheck_delegates_to_owner_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_product(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, dict(payload)))
        return {"status": "ok", "healthy": True}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    result = call_tool("orchestrator.healthcheck", {})

    assert result == {"status": "ok", "healthy": True}
    assert calls == [("orchestrator", {"action": "healthcheck"})]


def test_orchestrator_reset_loads_active_context_and_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ui_state = {
        "input_folder": str(tmp_path / "Input"),
        "artifact_folder": str(tmp_path / "Artifacts"),
        "corpus_output_folder": str(tmp_path / "Artifacts" / "Corpus"),
        "selected_corpus_db_path": str(tmp_path / "Artifacts" / "Corpus" / "active.db"),
        "semantic_release_mode": "database_default",
        "semantic_release_path": "",
    }
    state_path = tmp_path / "orchestrator" / "state" / "ui_state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(ui_state), encoding="utf-8")
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_product(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, dict(payload)))
        return {"status": "ok", "cleared_records": 2, "restored_sources": 1, "renamed_conflicts": 0, "removed_targets": 3}

    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: state_path)
    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    result = call_tool("orchestrator.reset", {})

    assert result["status"] == "ok"
    assert calls == [("orchestrator", {"action": "reset", "ui_state": ui_state})]


def test_orchestrator_reset_fails_closed_without_active_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: tmp_path / "missing-ui-state.json")
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="kein aktiver Pipeline-Kontext"):
        call_tool("orchestrator.reset", {})

    assert calls == []
