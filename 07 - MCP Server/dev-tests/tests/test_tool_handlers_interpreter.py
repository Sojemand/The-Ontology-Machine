from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions

RUNTIME_POLICY = {
    "LOG_LEVEL": "INFO",
    "DEBUG_BUNDLE_DIR": "",
    "PAGE_ASSET_ALLOWED_ROOTS": "",
    "OPENAI_API_BASE_URL": "https://api.openai.com/v1",
}


def test_interpreter_edit_tools_are_visible_with_flat_schemas() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    expected = {
        "interpreter.describe_surfaces": (set(), set()),
        "interpreter.read_surface": ({"surface_id"}, {"surface_id"}),
        "interpreter.validate_surface": ({"surface_id", "value"}, {"surface_id", "value"}),
        "interpreter.write_surface": ({"surface_id", "value"}, {"surface_id", "value"}),
    }

    assert set(expected) <= set(tools)
    for name, (properties, required) in expected.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == properties
        assert set(schema["required"]) == required
        assert "action" not in schema["properties"]
        assert "payload" not in schema["properties"]
        assert "path" not in schema["properties"]


def test_interpreter_edit_tools_delegate_exact_owner_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs))
        return {"status": "ok", "value": {"LOG_LEVEL": "INFO"}}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    call_tool("interpreter.describe_surfaces", {})
    call_tool("interpreter.read_surface", {"surface_id": "interpreter.runtime_policy_env"})
    call_tool("interpreter.validate_surface", {"surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY})
    call_tool("interpreter.write_surface", {"surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY})

    assert calls == [
        ("interpreter", {"action": "describe_surfaces"}, {}),
        ("interpreter", {"action": "read_surface", "surface_id": "interpreter.runtime_policy_env"}, {}),
        ("interpreter", {"action": "validate_surface", "surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY}, {}),
        ("interpreter", {"action": "write_surface", "surface_id": "interpreter.runtime_policy_env", "value": RUNTIME_POLICY}, {}),
    ]


def test_interpreter_guards_reject_paths_and_secrets_before_owner_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_edit", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="source_path"):
        call_tool("interpreter.read_surface", {"surface_id": "interpreter.runtime_policy_env", "source_path": "runtime/cache"})
    with pytest.raises(ToolFailure, match="Credential-Feld"):
        call_tool(
            "interpreter.validate_surface",
            {"surface_id": "interpreter.runtime_policy_env", "value": {"OPENAI_API_KEY": "sk-secretvalue123456"}},
        )

    assert calls == []


def test_interpreter_output_secret_guard_blocks_owner_leaks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tool_handlers,
        "_invoke_edit",
        lambda *_args, **_kwargs: {"status": "ok", "value": {"OPENAI_API_KEY": "sk-leakysecret123456"}},
    )

    with pytest.raises(ToolFailure, match="Credential-Feld"):
        call_tool("interpreter.read_surface", {"surface_id": "interpreter.runtime_policy_env"})


def test_interpreter_real_owner_validate_does_not_write_and_write_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "interpreter-home"
    monkeypatch.setenv("INTERPRETER_HOME", str(home))
    env_file = home / "config" / ".env"

    described = call_tool("interpreter.describe_surfaces", {})
    current = call_tool("interpreter.read_surface", {"surface_id": "interpreter.runtime_policy_env"})
    unknown = call_tool("interpreter.read_surface", {"surface_id": "interpreter.unknown"})
    validated = call_tool(
        "interpreter.validate_surface",
        {"surface_id": "interpreter.runtime_policy_env", "value": current["value"]},
    )
    limits = call_tool("interpreter.read_surface", {"surface_id": "interpreter.execution_limits"})
    invalid_limits = dict(limits["value"])
    invalid_limits["MAX_WORKERS"] = 0
    failed_write = call_tool(
        "interpreter.write_surface",
        {"surface_id": "interpreter.execution_limits", "value": invalid_limits},
    )

    valid_limits = dict(limits["value"])
    valid_limits["MAX_WORKERS"] = 2
    written = call_tool("interpreter.write_surface", {"surface_id": "interpreter.execution_limits", "value": valid_limits})

    assert described["status"] == "ok"
    assert [surface["surface_id"] for surface in described["surfaces"]]
    assert current["value"] == RUNTIME_POLICY
    assert unknown["status"] == "error"
    assert "Unbekannte Surface" in unknown["reason"]
    assert validated["status"] == "ok"
    assert failed_write["status"] == "error"
    assert "MAX_WORKERS muss > 0" in failed_write["reason"]
    assert written["status"] == "ok"
    assert "MAX_WORKERS=2" in env_file.read_text(encoding="utf-8")
