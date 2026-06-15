from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool


def test_optimizer_extract_document_delegates_exact_owner_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root = tmp_path / "Input"
    output_root = tmp_path / "Output"
    input_root.mkdir()
    output_root.mkdir()
    source_path = input_root / "source.pdf"
    source_path.write_text("pdf placeholder", encoding="utf-8")
    runtime_policy_path = tmp_path / "runtime_policy.json"
    runtime_policy_path.write_text("{}", encoding="utf-8")
    raw_output_path = output_root / "raw" / "source.raw.json"
    page_images_dir = output_root / "page_images" / "source"
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "ok", "raw_path": str(raw_output_path)}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "optimizer.extract_document",
        {
            "source_path": str(source_path),
            "input_root": str(input_root),
            "output_root": str(output_root),
            "raw_output_path": str(raw_output_path),
            "page_images_dir": str(page_images_dir),
            "logical_source_path": "Input/source.pdf",
            "optimizer_profile": "vision",
            "runtime_policy_path": str(runtime_policy_path),
            "timeout_seconds": 30,
        },
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "optimizer",
            {
                "action": "extract_document",
                "source_path": str(source_path.resolve()),
                "input_root": str(input_root.resolve()),
                "output_root": str(output_root.resolve()),
                "raw_output_path": str(raw_output_path.resolve()),
                "page_images_dir": str(page_images_dir.resolve()),
                "logical_source_path": "Input/source.pdf",
                "optimizer_profile": "vision",
                "runtime_policy_path": str(runtime_policy_path.resolve()),
            },
            {"timeout": 30},
        )
    ]


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("optimizer.extract_document", {"optimizer_profile": "vision"}, "source_path fehlt"),
        ("optimizer.extract_document", {"source_path": "x"}, "input_root fehlt"),
        ("optimizer.healthcheck", {"required_dependencies": ["unknown-runtime"]}, "unbekannte Abhaengigkeit"),
        ("optimizer.scan_debug_input", {"input_root": "x"}, "debug_root fehlt"),
    ],
)
def test_optimizer_tools_reject_bad_arguments_before_owner_call(
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


def test_optimizer_extract_rejects_output_escape_before_owner_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_root = tmp_path / "Input"
    output_root = tmp_path / "Output"
    input_root.mkdir()
    output_root.mkdir()
    source_path = input_root / "source.txt"
    source_path.write_text("source", encoding="utf-8")
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="raw_output_path muss innerhalb von output_root liegen"):
        call_tool(
            "optimizer.extract_document",
            {
                "source_path": str(source_path),
                "input_root": str(input_root),
                "output_root": str(output_root),
                "raw_output_path": str(tmp_path / "outside.raw.json"),
                "page_images_dir": str(output_root / "pages"),
                "logical_source_path": "source.txt",
                "optimizer_profile": "file",
            },
        )

    assert calls == []
