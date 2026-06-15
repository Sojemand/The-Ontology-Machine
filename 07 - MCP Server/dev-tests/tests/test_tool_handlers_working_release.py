from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.governance import NORMALIZER_SOURCE_ACTIONS
from mcp_server.tools import ToolFailure, call_tool, tool_definitions


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_payload"),
    [
        ("read_working_release", {}, {"action": "read_release_package"}),
        ("list_working_release_profiles", {}, {"action": "list_projections"}),
        ("read_working_release_profile", {"projection_id": "finance.default.v1"}, {"action": "read_projection", "projection_id": "finance.default.v1"}),
        ("validate_working_release", {"target_locale": "de"}, {"action": "validate_release_package", "target_locale": "de"}),
        ("compile_working_release", {"target_locale": "en"}, {"action": "compile_release_package", "target_locale": "en"}),
        ("preview_working_release_impact", {}, {"action": "preview_impact"}),
        (
            "create_working_release_package",
            {"default_runtime_locale": "de", "projection_ids": ["finance.default.v1"]},
            {
                "action": "create_release_package",
                "default_runtime_locale": "de",
                "projection_ids": ["finance.default.v1"],
            },
        ),
        (
            "export_working_release",
            {"output_path": "release.semantic_release.json", "target_locale": "de"},
            {"action": "export_semantic_release", "output_path": "release.semantic_release.json", "target_locale": "de"},
        ),
    ],
)
def test_working_release_tools_use_workspace_normalizer_home(
    tool_name: str,
    arguments: dict[str, Any],
    expected_payload: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_folder = tmp_path / "workspace"
    if "output_path" in arguments:
        arguments = {**arguments, "output_path": str(tmp_path / arguments["output_path"])}
        expected_payload = {**expected_payload, "output_path": arguments["output_path"]}
    arguments = {"artifact_folder": str(artifact_folder), **arguments}
    calls: list[tuple[str, dict[str, Any], dict[str, str] | None]] = []

    def fake_invoke(
        module_key: str,
        payload: dict[str, Any],
        *,
        env_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        calls.append((module_key, payload, env_overrides))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool(tool_name, arguments)

    normalizer_home = artifact_folder.resolve() / ".vp" / "n"
    assert result["status"] == "ok"
    assert result["authoring_scope"] == "workspace"
    assert result["normalizer_authoring_home"] == str(normalizer_home)
    assert calls == [("normalizer", expected_payload, {"NORMALIZER_VISION_HOME": str(normalizer_home)})]


def test_export_working_release_rejects_mcp_semantic_release_state_before_owner_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)
    forbidden_path = Path(tool_handlers.__file__).resolve().parents[1] / "state" / "semantic_releases" / "release.json"

    with pytest.raises(ToolFailure, match="state/semantic_releases"):
        call_tool(
            "export_working_release",
            {"artifact_folder": str(tmp_path / "workspace"), "output_path": str(forbidden_path)},
        )

    assert calls == []


def test_working_release_tool_schemas_are_flat_and_exact() -> None:
    expected_schemas = {
        "read_working_release": ({"artifact_folder"}, {"artifact_folder"}),
        "list_working_release_profiles": ({"artifact_folder"}, {"artifact_folder"}),
        "read_working_release_profile": ({"artifact_folder", "projection_id"}, {"artifact_folder", "projection_id"}),
        "validate_working_release": ({"artifact_folder", "target_locale"}, {"artifact_folder"}),
        "compile_working_release": ({"artifact_folder", "target_locale"}, {"artifact_folder"}),
        "preview_working_release_impact": ({"artifact_folder"}, {"artifact_folder"}),
        "create_working_release_package": ({"artifact_folder", "default_runtime_locale", "projection_ids"}, {"artifact_folder"}),
        "export_working_release": ({"artifact_folder", "output_path", "target_locale"}, {"artifact_folder", "output_path"}),
    }
    tools = {tool["name"]: tool for tool in tool_definitions()}

    for name, (expected_properties, expected_required) in expected_schemas.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == expected_properties
        assert set(schema["required"]) == expected_required
        assert "payload" not in schema["properties"]


def test_working_release_profile_owner_action_is_mcp_governed() -> None:
    assert "read_projection" in NORMALIZER_SOURCE_ACTIONS
    assert "create_release_package" in NORMALIZER_SOURCE_ACTIONS


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("read_working_release", {}, "artifact_folder fehlt"),
        ("list_working_release_profiles", {}, "artifact_folder fehlt"),
        ("read_working_release_profile", {"artifact_folder": "x"}, "projection_id fehlt"),
        ("validate_working_release", {"artifact_folder": "x", "target_locale": "german"}, "target_locale muss ein gueltiger Locale-Code"),
        ("compile_working_release", {"artifact_folder": "x", "target_locale": "german"}, "target_locale muss ein gueltiger Locale-Code"),
        ("preview_working_release_impact", {}, "artifact_folder fehlt"),
        ("create_working_release_package", {}, "artifact_folder fehlt"),
        ("create_working_release_package", {"artifact_folder": "x", "default_runtime_locale": "german"}, "default_runtime_locale muss ein gueltiger Locale-Code"),
        ("create_working_release_package", {"artifact_folder": "x", "projection_ids": "finance.default.v1"}, "projection_ids muss eine String-Liste"),
        ("export_working_release", {"artifact_folder": "x"}, "output_path fehlt"),
    ],
)
def test_working_release_tools_reject_bad_arguments_before_owner_call(
    tool_name: str,
    arguments: dict[str, Any],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_edit", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match=message):
        call_tool(tool_name, arguments)

    assert calls == []
