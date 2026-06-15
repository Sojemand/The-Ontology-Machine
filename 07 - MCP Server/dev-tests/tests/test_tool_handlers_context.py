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

def test_activate_corpus_context_delegates_to_both_owners(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    corpus_root = tmp_path / "Corpus"
    corpus_root.mkdir()
    corpus_db = corpus_root / "corpus.db"
    corpus_db.write_bytes(b"SQLite format 3\x00")
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok", "module": module_key}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "activate_corpus_context",
        {"corpus_db_path": str(corpus_db), "corpus_output_folder": str(corpus_root)},
    )

    assert result["status"] == "ok"
    assert calls == [
        ("corpus_builder", {"action": "activate_corpus_context", "corpus_db_path": str(corpus_db)}),
        (
            "orchestrator",
            {
                "action": "activate_corpus_context",
                "corpus_db_path": str(corpus_db),
                "corpus_output_folder": str(corpus_root),
            },
        ),
    ]


def test_create_empty_corpus_db_uses_only_owner_create(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    corpus_root = tmp_path / "Corpus"
    corpus_root.mkdir()
    corpus_db = corpus_root / "fresh.db"
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        if payload["action"] == "create_empty_corpus_db":
            corpus_db.write_bytes(b"SQLite format 3\x00")
        return {"status": "ok", "module": module_key}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "create_empty_corpus_db",
        {"corpus_db_path": str(corpus_db), "corpus_output_folder": str(corpus_root)},
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "corpus_builder",
            {"action": "create_empty_corpus_db", "corpus_db_path": str(corpus_db), "activate_context": False},
        )
    ]


def test_prepare_pipeline_workspace_root_creates_only_expected_folders(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    artifact_root = tmp_path / "Artifacts Test"
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok", "module": module_key}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "prepare_pipeline_workspace_root",
        {"artifact_folder": str(artifact_root)},
    )

    assert result["status"] == "ok"
    assert result["artifact_folder"] == str(artifact_root.resolve())
    assert result["corpus_output_folder"] == str((artifact_root / "Corpus").resolve())
    assert (artifact_root / "Input").is_dir()
    assert (artifact_root / "Documents" / "normalized").is_dir()
    assert (artifact_root / "Documents" / "structured").is_dir()
    assert (artifact_root / "Error Cases").is_dir()
    assert calls == []
