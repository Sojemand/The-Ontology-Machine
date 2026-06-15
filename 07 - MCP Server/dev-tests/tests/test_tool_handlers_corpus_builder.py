from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions


def test_corpus_builder_pipeline_atom_tools_are_visible_with_flat_schemas() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    expected = {
        "corpus_builder.load_document": (
            {
                "artifact_root",
                "normalized_path",
                "structured_path",
                "validation_path",
                "raw_path",
                "corpus_db_path",
                "corpus_output_folder",
                "persist_page_images_in_db",
                "page_images_dir",
                "timeout_seconds",
            },
            {
                "artifact_root",
                "normalized_path",
                "structured_path",
                "validation_path",
                "corpus_db_path",
                "corpus_output_folder",
            },
        ),
        "corpus_builder.healthcheck": ({"runtime_model", "scope", "timeout_seconds"}, {"runtime_model"}),
        "corpus_builder.scan_debug_input": (
            {"input_root", "debug_root", "session_root", "timeout_seconds"},
            {"input_root", "debug_root", "session_root"},
        ),
    }

    assert set(expected) <= set(tools)
    for name, (properties, required) in expected.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == properties
        assert set(schema["required"]) == required
        assert "action" not in schema["properties"]
        assert "payload" not in schema["properties"]


def test_corpus_builder_load_document_delegates_exact_owner_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_root = tmp_path / "artifacts"
    corpus_root = tmp_path / "Corpus"
    page_images_dir = artifact_root / "page_images" / "invoice"
    artifact_root.mkdir()
    corpus_root.mkdir()
    page_images_dir.mkdir(parents=True)
    normalized_path = artifact_root / "invoice.structured.normalized.json"
    structured_path = artifact_root / "invoice.structured.json"
    validation_path = artifact_root / "invoice.validation_report.json"
    raw_path = artifact_root / "invoice.raw.json"
    for path in (normalized_path, structured_path, validation_path, raw_path):
        path.write_text("{}", encoding="utf-8")
    corpus_db_path = corpus_root / "corpus.db"
    corpus_db_path.write_bytes(b"SQLite format 3\x00")
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "loaded", "reason": ""}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "corpus_builder.load_document",
        {
            "artifact_root": str(artifact_root),
            "normalized_path": str(normalized_path),
            "structured_path": str(structured_path),
            "validation_path": str(validation_path),
            "raw_path": str(raw_path),
            "corpus_db_path": str(corpus_db_path),
            "corpus_output_folder": str(corpus_root),
            "persist_page_images_in_db": False,
            "page_images_dir": str(page_images_dir),
            "timeout_seconds": 45,
        },
    )

    assert result["status"] == "loaded"
    assert calls == [
        (
            "corpus_builder",
            {
                "action": "load_document",
                "corpus_db_path": str(corpus_db_path.resolve()),
                "normalized_path": str(normalized_path.resolve()),
                "structured_path": str(structured_path.resolve()),
                "validation_path": str(validation_path.resolve()),
                "raw_path": str(raw_path.resolve()),
                "persist_page_images_in_db": False,
                "page_images_dir": str(page_images_dir.resolve()),
            },
            {"timeout": 45},
        )
    ]


def test_corpus_builder_healthcheck_delegates_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "ok", "healthy": True}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "corpus_builder.healthcheck",
        {"runtime_model": "text-embedding-3-small", "scope": "pipeline_run", "timeout_seconds": 15},
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "corpus_builder",
            {
                "action": "healthcheck",
                "runtime_settings": {"model": "text-embedding-3-small"},
                "scope": "pipeline_run",
            },
            {"timeout": 15},
        )
    ]


def test_corpus_builder_scan_debug_input_bounds_session_and_delegates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "artifacts"
    debug_root = tmp_path / "debug"
    input_root.mkdir()
    debug_root.mkdir()
    session_root = debug_root / "scan-session"
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "ok", "metrics": {"bundle_count": 1}}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "corpus_builder.scan_debug_input",
        {
            "input_root": str(input_root),
            "debug_root": str(debug_root),
            "session_root": "scan-session",
            "timeout_seconds": 30,
        },
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "corpus_builder",
            {
                "action": "scan_debug_input",
                "input_root": str(input_root.resolve()),
                "session_root": str(session_root.resolve()),
                "mode": "scan",
            },
            {"timeout": 30},
        )
    ]
