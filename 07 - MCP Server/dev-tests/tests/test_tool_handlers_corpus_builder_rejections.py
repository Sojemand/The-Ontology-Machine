from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("corpus_builder.load_document", {}, "artifact_root fehlt"),
        ("corpus_builder.healthcheck", {}, "runtime_model fehlt"),
        ("corpus_builder.scan_debug_input", {}, "input_root fehlt"),
    ],
)
def test_corpus_builder_tools_reject_bad_arguments_before_owner_call(
    tool_name: str,
    arguments: dict[str, Any],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match=message):
        call_tool(tool_name, arguments)

    assert calls == []


def test_corpus_builder_load_document_rejects_missing_db_before_owner_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_root = tmp_path / "artifacts"
    corpus_root = tmp_path / "Corpus"
    artifact_root.mkdir()
    corpus_root.mkdir()
    normalized_path = artifact_root / "invoice.structured.normalized.json"
    structured_path = artifact_root / "invoice.structured.json"
    validation_path = artifact_root / "invoice.validation_report.json"
    for path in (normalized_path, structured_path, validation_path):
        path.write_text("{}", encoding="utf-8")
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="corpus_db_path existiert nicht"):
        call_tool(
            "corpus_builder.load_document",
            {
                "artifact_root": str(artifact_root),
                "normalized_path": str(normalized_path),
                "structured_path": str(structured_path),
                "validation_path": str(validation_path),
                "corpus_db_path": str(corpus_root / "missing.db"),
                "corpus_output_folder": str(corpus_root),
            },
        )

    assert calls == []


def test_corpus_builder_scan_rejects_session_escape_before_owner_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "artifacts"
    debug_root = tmp_path / "debug"
    input_root.mkdir()
    debug_root.mkdir()
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="session_root muss innerhalb von debug_root liegen"):
        call_tool(
            "corpus_builder.scan_debug_input",
            {
                "input_root": str(input_root),
                "debug_root": str(debug_root),
                "session_root": str(tmp_path / "outside-session"),
            },
        )

    assert calls == []
