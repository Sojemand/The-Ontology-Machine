from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mcp_server import support_monitor, tool_handlers
from mcp_server.contract_client import ContractError
from mcp_server.tools import ToolFailure, call_tool

def test_reset_active_corpus_db_delegates_to_corpus_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    call_tool(
        "reset_active_corpus_db",
        {"corpus_db_path": "C:/tmp/corpus.db", "confirmation_artifact_path": "C:/tmp/confirm.json"},
    )

    assert calls == [
        (
            "corpus_builder",
            {
                "action": "reset_active_corpus_db",
                "corpus_db_path": "C:/tmp/corpus.db",
                "confirmation_artifact_path": "C:/tmp/confirm.json",
            },
        )
    ]


def test_activate_release_on_existing_db_delegates_only_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    product_calls: list[tuple[str, dict[str, Any]]] = []

    def fake_product(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        product_calls.append((module_key, payload))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    result = call_tool(
        "activate_release_on_existing_db",
        {"release_path": "C:/tmp/release.json", "corpus_db_path": "C:/tmp/corpus.db"},
    )

    assert result["status"] == "ok"
    assert product_calls == [
        (
            "corpus_builder",
            {
                "action": "activate_semantic_release",
                "release_path": "C:/tmp/release.json",
                "corpus_db_path": "C:/tmp/corpus.db",
                "write_global_mirrors": False,
            },
        )
    ]


def test_owner_contract_errors_are_recorded_as_support_incidents(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(support_monitor, "state_root", lambda: tmp_path / "support")

    def fake_product(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise ContractError(f"{module_key}:{payload['action']} failed with token sk-handlersecret123456")

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)

    with pytest.raises(ToolFailure, match="failed"):
        call_tool("semantic_audit", {"corpus_db_path": "C:/tmp/corpus.db"})

    incidents = support_monitor.list_incidents()
    dumped = str(incidents)
    assert incidents["incident_count"] == 1
    assert incidents["incidents"][0]["action"] == "semantic_audit"
    assert "sk-handlersecret" not in dumped


def test_admin_tools_delegate_to_orchestrator_admin_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_admin(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_admin", fake_admin)

    call_tool("read_runtime_settings", {})
    call_tool("inspect_runtime_credentials", {})
    call_tool(
        "reveal_secret",
        {
            "target": "llm_shared",
            "purpose": "test",
            "unlock_phrase": "REVEAL_SECRET:llm_shared",
        },
    )

    assert [call[1]["action"] for call in calls] == [
        "manage_runtime_settings",
        "manage_credentials",
        "reveal_secret",
    ]
