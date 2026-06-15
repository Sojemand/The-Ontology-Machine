from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions


def test_interpreter_and_validator_pipeline_tools_are_visible_with_stage_clean_schemas() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    expected = {
        "interpreter.interpret_document": (
            {
                "request_root",
                "request_path",
                "output_root",
                "structured_output_path",
                "runtime_settings",
                "debug_bundle_dir",
                "timeout_seconds",
            },
            {"request_root", "request_path", "output_root", "structured_output_path", "runtime_settings"},
        ),
        "interpreter.healthcheck": ({"runtime_settings", "timeout_seconds"}, {"runtime_settings"}),
        "validator.validate_document": (
            {
                "structured_root",
                "structured_path",
                "validation_root",
                "validation_output_path",
                "raw_root",
                "raw_path",
                "timeout_seconds",
            },
            {"structured_root", "structured_path", "validation_root", "validation_output_path"},
        ),
        "validator.healthcheck": ({"timeout_seconds"}, set()),
    }

    assert set(expected) <= set(tools)
    for name, (properties, required) in expected.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == properties
        assert set(schema["required"]) == required
        assert "action" not in schema["properties"]
        assert "payload" not in schema["properties"]


def test_interpreter_interpret_document_delegates_exact_owner_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_root = tmp_path / "requests"
    output_root = tmp_path / "structured"
    request_root.mkdir()
    output_root.mkdir()
    request_path = request_root / "invoice.interpreter_request.json"
    request_path.write_text("{}", encoding="utf-8")
    structured_output_path = output_root / "invoice.structured.json"
    debug_bundle_dir = output_root / "debug" / "invoice"
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "ok", "structured_path": str(structured_output_path)}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "interpreter.interpret_document",
        {
            "request_root": str(request_root),
            "request_path": str(request_path),
            "output_root": str(output_root),
            "structured_output_path": str(structured_output_path),
            "runtime_settings": {"model": "gpt-test", "max_output_tokens": 4096},
            "debug_bundle_dir": str(debug_bundle_dir),
            "timeout_seconds": 30,
        },
    )

    assert result["status"] == "ok"
    assert calls == [
        (
            "interpreter",
            {
                "action": "interpret_document",
                "request_path": str(request_path.resolve()),
                "structured_output_path": str(structured_output_path.resolve()),
                "runtime_settings": {"model": "gpt-test", "max_output_tokens": 4096},
                "debug_bundle_dir": str(debug_bundle_dir.resolve()),
            },
            {"timeout": 30},
        )
    ]


def test_validator_validate_document_delegates_exact_owner_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    structured_root = tmp_path / "structured"
    raw_root = tmp_path / "raw"
    validation_root = tmp_path / "validation"
    for folder in (structured_root, raw_root, validation_root):
        folder.mkdir()
    structured_path = structured_root / "invoice.structured.json"
    raw_path = raw_root / "invoice.raw.json"
    report_path = validation_root / "invoice.vision_validation_report.json"
    structured_path.write_text("{}", encoding="utf-8")
    raw_path.write_text("{}", encoding="utf-8")
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "PASS", "report_path": str(report_path)}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "validator.validate_document",
        {
            "structured_root": str(structured_root),
            "structured_path": str(structured_path),
            "validation_root": str(validation_root),
            "validation_output_path": str(report_path),
            "raw_root": str(raw_root),
            "raw_path": str(raw_path),
            "timeout_seconds": 45,
        },
    )

    assert result["status"] == "PASS"
    assert calls == [
        (
            "validator",
            {
                "action": "validate_document",
                "structured_path": str(structured_path.resolve()),
                "validation_output_path": str(report_path.resolve()),
                "raw_path": str(raw_path.resolve()),
            },
            {"timeout": 45},
        )
    ]


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("interpreter.interpret_document", {"request_root": "x"}, "request_path fehlt"),
        ("interpreter.healthcheck", {"runtime_settings": {"model": "gpt-test", "max_output_tokens": 0}}, "max_output_tokens muss eine positive Ganzzahl"),
        ("validator.validate_document", {"structured_root": "x"}, "structured_path fehlt"),
        ("validator.validate_document", {"raw_path": "x"}, "structured_root fehlt"),
    ],
)
def test_interpreter_and_validator_tools_reject_bad_arguments_before_owner_call(
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
