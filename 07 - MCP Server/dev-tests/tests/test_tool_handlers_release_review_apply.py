from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mcp_server import support_monitor, tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions

BOOTSTRAP_ARGS = {
    "goal": "Fantasy story archive",
    "must_keep": "characters and places",
    "noise_tolerance": "medium",
}
DATA_ARGS = {
    "structured_sample_path": "structured.json",
    "expected_normalized_path": "normalized.json",
    "sample_label": "Sample One",
}


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_payload"),
    [
        ("review_bootstrap_release", BOOTSTRAP_ARGS, {"action": "review_bootstrap_release", **BOOTSTRAP_ARGS}),
        (
            "apply_bootstrap_release",
            {**BOOTSTRAP_ARGS, "user_confirmed": True},
            {"action": "bootstrap_release_package", **BOOTSTRAP_ARGS},
        ),
        (
            "review_data_informed_release",
            {**DATA_ARGS, "original_reference_path": "original.pdf"},
            {"action": "review_data_informed_release", **DATA_ARGS, "original_reference_path": "original.pdf"},
        ),
        (
            "refine_working_release_from_sample",
            {**DATA_ARGS, "user_confirmed": True},
            {"action": "refine_release_package", **DATA_ARGS},
        ),
    ],
)
def test_release_review_apply_tools_send_exact_owner_payloads(
    tool_name: str,
    arguments: dict[str, Any],
    expected_payload: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any], dict[str, str] | None]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs.get("env_overrides")))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)
    artifact_folder = tmp_path / "workspace"

    result = call_tool(tool_name, {"artifact_folder": str(artifact_folder), **arguments})

    normalizer_home = artifact_folder.resolve() / ".vp" / "n"
    assert result["status"] == "ok"
    assert calls == [("normalizer", expected_payload, {"NORMALIZER_VISION_HOME": str(normalizer_home)})]


def test_release_review_apply_tool_schemas_are_flat() -> None:
    expected = {
        "review_bootstrap_release": ({"artifact_folder", "goal", "must_keep", "noise_tolerance"}, {"artifact_folder", "goal", "must_keep", "noise_tolerance"}),
        "apply_bootstrap_release": (
            {"artifact_folder", "goal", "must_keep", "noise_tolerance", "user_confirmed", "expected_candidate_fingerprint"},
            {"artifact_folder", "goal", "must_keep", "noise_tolerance", "user_confirmed"},
        ),
        "review_data_informed_release": (
            {"artifact_folder", "structured_sample_path", "expected_normalized_path", "original_reference_path", "sample_label"},
            {"artifact_folder", "structured_sample_path", "expected_normalized_path"},
        ),
        "refine_working_release_from_sample": (
            {"artifact_folder", "structured_sample_path", "expected_normalized_path", "original_reference_path", "sample_label", "user_confirmed", "expected_candidate_fingerprint"},
            {"artifact_folder", "structured_sample_path", "expected_normalized_path", "user_confirmed"},
        ),
    }
    tools = {tool["name"]: tool for tool in tool_definitions()}

    for name, (properties, required) in expected.items():
        schema = tools[name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == properties
        assert set(schema["required"]) == required
        assert "payload" not in schema["properties"]


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("review_bootstrap_release", {"artifact_folder": "x", "must_keep": "keep", "noise_tolerance": "medium"}, "goal fehlt"),
        ("review_bootstrap_release", {"artifact_folder": "x", **BOOTSTRAP_ARGS, "noise_tolerance": "none"}, "noise_tolerance muss"),
        ("apply_bootstrap_release", {"artifact_folder": "x", **BOOTSTRAP_ARGS}, "user_confirmed fehlt"),
        ("review_data_informed_release", {"artifact_folder": "x", "structured_sample_path": "structured.json"}, "expected_normalized_path fehlt"),
        ("refine_working_release_from_sample", {"artifact_folder": "x", **DATA_ARGS, "user_confirmed": False}, "user_confirmed=true"),
    ],
)
def test_release_review_apply_tools_reject_bad_arguments_before_owner_call(
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


def test_review_bootstrap_release_records_candidate_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(support_monitor, "state_root", lambda: tmp_path / "support")
    monkeypatch.setattr(tool_handlers, "_invoke_edit", lambda *_args, **_kwargs: {"status": "ok", "candidate_release_fingerprint": "candidate-fp-1"})

    result = call_tool("review_bootstrap_release", {"artifact_folder": str(tmp_path / "workspace"), **BOOTSTRAP_ARGS})

    checkpoint_path = tmp_path / "support" / "release_review_checkpoints.jsonl"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8").splitlines()[0])
    assert result["mcp_review_checkpoint"]["recorded"] is True
    assert checkpoint["workflow_kind"] == "bootstrap"
    assert checkpoint["artifact_folder"] == str((tmp_path / "workspace").resolve())
    assert checkpoint["candidate_fingerprint"] == "candidate-fp-1"


def test_apply_bootstrap_release_accepts_matching_review_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(support_monitor, "state_root", lambda: tmp_path / "support")
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload))
        if payload["action"] == "review_bootstrap_release":
            return {"status": "ok", "candidate_release_fingerprint": "candidate-fp-2"}
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    call_tool("review_bootstrap_release", {"artifact_folder": str(tmp_path / "workspace"), **BOOTSTRAP_ARGS})
    result = call_tool(
        "apply_bootstrap_release",
        {"artifact_folder": str(tmp_path / "workspace"), **BOOTSTRAP_ARGS, "user_confirmed": True, "expected_candidate_fingerprint": "candidate-fp-2"},
    )

    assert result["mcp_apply_safety"]["verified_review_checkpoint"] is True
    assert [payload["action"] for _module, payload in calls] == ["review_bootstrap_release", "bootstrap_release_package"]


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("apply_bootstrap_release", {**BOOTSTRAP_ARGS, "user_confirmed": True, "expected_candidate_fingerprint": "missing-fp"}),
        ("refine_working_release_from_sample", {**DATA_ARGS, "user_confirmed": True, "expected_candidate_fingerprint": "missing-fp"}),
    ],
)
def test_apply_tools_reject_missing_expected_checkpoint_before_owner_call(
    tool_name: str,
    arguments: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(support_monitor, "state_root", lambda: tmp_path / "support")
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_edit", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="Kein passender Review-Checkpoint"):
        call_tool(tool_name, {"artifact_folder": str(tmp_path / "workspace"), **arguments})

    assert calls == []
