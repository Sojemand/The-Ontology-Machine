from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from mcp_server import support_monitor, tool_handlers
from mcp_server.contract_client import ContractError
from mcp_server.tools import ToolFailure, call_tool

def test_activation_preflight_delegates_to_corpus_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok", "payload": payload}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "activation_preflight",
        {"release_path": "C:/tmp/release.json", "corpus_db_path": "C:/tmp/corpus.db"},
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "corpus_builder",
            {
                "action": "activation_preflight",
                "release_path": "C:/tmp/release.json",
                "corpus_db_path": "C:/tmp/corpus.db",
            },
        )
    ]


def test_create_locale_scaffold_uses_workspace_flat_arguments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any], dict[str, str] | None]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs.get("env_overrides")))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)
    artifact_folder = tmp_path / "workspace"

    call_tool(
        "create_locale_scaffold",
        {
            "artifact_folder": str(artifact_folder),
            "source_locale": "en",
            "target_locale": "fr",
            "overwrite_existing": True,
        },
    )
    normalizer_home = artifact_folder.resolve() / ".vp" / "n"

    assert calls == [
        (
            "normalizer",
            {
                "action": "create_locale_scaffold",
                "source_locale": "en",
                "target_locale": "fr",
                "overwrite_existing": True,
            },
            {"NORMALIZER_VISION_HOME": str(normalizer_home)},
        )
    ]


def test_inspect_source_document_sample_delegates_to_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok", "excerpt": {"chunks": ["sample"]}}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "inspect_source_document_sample",
        {
            "source_document_path": "C:/tmp/Fantasy Story.txt",
            "sample_label": "Fantasy sample",
            "max_excerpt_chars": 7000,
            "timeout_seconds": 30,
            "cleanup_days": 0,
        },
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "orchestrator",
            {
                "action": "inspect_source_document_sample",
                "source_document_path": "C:/tmp/Fantasy Story.txt",
                "sample_label": "Fantasy sample",
                "max_excerpt_chars": 7000,
                "timeout_seconds": 30,
                "cleanup_days": 0,
            },
        )
    ]


def test_owner_surface_writes_use_owner_value_key(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    call_tool(
        "validate_owner_surface",
        {"module": "orchestrator", "surface_id": "orchestrator.execution_policy", "value": {"enabled": True}},
    )

    assert calls == [
        (
            "orchestrator",
            {
                "action": "validate_surface",
                "surface_id": "orchestrator.execution_policy",
                "value": {"enabled": True},
            },
        )
    ]
