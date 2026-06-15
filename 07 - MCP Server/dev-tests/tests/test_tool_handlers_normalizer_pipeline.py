from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool, tool_definitions

RUNTIME_SETTINGS = {"model": "gpt-test", "max_output_tokens": 1000}
ACTIVE_RELEASE = {
    "release_id": "semantic_release.test",
    "release_version": "1.0.0",
    "master_taxonomy_id": "taxonomy.master",
    "master_taxonomy_version": "1",
    "projection_ids": ["finance.default.v1"],
    "materialization_version": "1",
    "fingerprint": "sha256:test-release",
    "master_taxonomy": {"axes": {}},
    "projections": [{"projection_id": "finance.default.v1", "label": "Finance", "routing": {"surface_signals": {}}}],
}

def test_normalizer_atomic_tools_are_visible_with_schemas() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    expected = {
        "normalizer.normalize_document": (
            {
                "structured_path",
                "structured_root",
                "normalized_output_path",
                "normalized_root",
                "corpus_db_path",
                "corpus_output_folder",
                "runtime_settings",
                "timeout_seconds",
            },
            {"structured_path", "structured_root", "normalized_output_path", "normalized_root", "corpus_db_path", "runtime_settings"},
        ),
        "normalizer.healthcheck": (
            {"runtime_settings", "corpus_db_path", "corpus_output_folder", "timeout_seconds"},
            {"runtime_settings"},
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
        assert "release" not in schema["properties"]
        assert tools[name]["outputSchema"]["properties"]["release_context"]


def test_normalizer_normalize_document_reads_active_release_then_delegates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _normalizer_paths(tmp_path)
    calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, dict(payload), kwargs))
        if module_key == "corpus_builder":
            return _active_release_response()
        return {"status": "OK", "output_path": payload["normalized_output_path"], "needs_review": False}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "normalizer.normalize_document",
        {
            **_tool_args(paths),
            "runtime_settings": RUNTIME_SETTINGS,
            "timeout_seconds": 44,
        },
    )

    assert result["status"] == "OK"
    assert result["release_context"]["source"] == "corpus_builder.read_active_semantic_release"
    assert [call[0] for call in calls] == ["corpus_builder", "normalizer"]
    assert calls[0] == (
        "corpus_builder",
        {"action": "read_active_semantic_release", "corpus_db_path": paths["corpus_db_path"]},
        {"timeout": 44},
    )
    assert calls[1][0] == "normalizer"
    assert calls[1][1]["action"] == "normalize_document"
    assert calls[1][1]["release"] == ACTIVE_RELEASE
    assert "release_path" not in calls[1][1]
    assert calls[1][2] == {"timeout": 44}


def test_normalizer_healthcheck_can_include_release_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _normalizer_paths(tmp_path)
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, dict(payload)))
        return _active_release_response() if module_key == "corpus_builder" else {"status": "OK", "healthy": True}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    result = call_tool(
        "normalizer.healthcheck",
        {"runtime_settings": RUNTIME_SETTINGS, "corpus_db_path": paths["corpus_db_path"]},
    )

    assert result["healthy"] is True
    assert result["release_context"]["release_id"] == ACTIVE_RELEASE["release_id"]
    assert calls == [
        ("corpus_builder", {"action": "read_active_semantic_release", "corpus_db_path": paths["corpus_db_path"]}),
        ("normalizer", {"action": "healthcheck", "runtime_settings": RUNTIME_SETTINGS}),
    ]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda args, _p: args.update({"release": ACTIVE_RELEASE}), "kennt diese Argumente nicht: release"),
        (lambda args, p: args.update({"normalized_output_path": str(p["outside"])}), "normalized_output_path muss innerhalb"),
        (lambda args, p: args.update({"structured_path": str(p["bad_structured"])}), "structured_path muss auf .structured.json enden"),
        (lambda args, _p: args.update({"runtime_settings": {"model": "gpt-test", "max_output_tokens": 0}}), "max_output_tokens muss eine positive"),
    ],
)
def test_normalizer_normalize_document_rejects_bad_arguments_before_owner_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate,
    message: str,
) -> None:
    paths = _normalizer_paths(tmp_path)
    arguments: dict[str, Any] = {**_tool_args(paths), "runtime_settings": RUNTIME_SETTINGS}
    mutate(arguments, paths)
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_product", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match=message):
        call_tool("normalizer.normalize_document", arguments)

    assert calls == []


def test_normalizer_normalize_document_fails_without_active_release_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _normalizer_paths(tmp_path)
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, dict(payload)))
        return {"status": "ok", "detail": {"status": {"runtime_truth_source": "none"}}}

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_invoke)

    with pytest.raises(ToolFailure, match="keinen release-Payload"):
        call_tool("normalizer.normalize_document", {**_tool_args(paths), "runtime_settings": RUNTIME_SETTINGS})

    assert calls == [("corpus_builder", {"action": "read_active_semantic_release", "corpus_db_path": paths["corpus_db_path"]})]


def _normalizer_paths(tmp_path: Path) -> dict[str, str]:
    structured_root = tmp_path / "structured"
    normalized_root = tmp_path / "normalized"
    corpus_root = tmp_path / "corpus"
    for folder in (structured_root, normalized_root, corpus_root):
        folder.mkdir()
    structured_path = structured_root / "story.structured.json"
    structured_path.write_text("{}", encoding="utf-8")
    bad_structured = structured_root / "story.json"
    bad_structured.write_text("{}", encoding="utf-8")
    corpus_db_path = corpus_root / "active.db"
    corpus_db_path.write_bytes(b"SQLite format 3\x00")
    return {
        "structured_path": str(structured_path.resolve()),
        "structured_root": str(structured_root.resolve()),
        "normalized_output_path": str((normalized_root / "story.structured.normalized.json").resolve()),
        "normalized_root": str(normalized_root.resolve()),
        "corpus_db_path": str(corpus_db_path.resolve()),
        "outside": str((tmp_path / "outside.json").resolve()),
        "bad_structured": str(bad_structured.resolve()),
    }


def _tool_args(paths: dict[str, str]) -> dict[str, str]:
    keys = ("structured_path", "structured_root", "normalized_output_path", "normalized_root", "corpus_db_path")
    return {key: paths[key] for key in keys}


def _active_release_response() -> dict[str, Any]:
    return {
        "status": "ok",
        "detail": {
            "status": {"runtime_truth_source": "db_active_snapshot"},
            "release": ACTIVE_RELEASE,
            "release_id": ACTIVE_RELEASE["release_id"],
            "release_version": ACTIVE_RELEASE["release_version"],
            "fingerprint": ACTIVE_RELEASE["fingerprint"],
            "active_snapshot": {"snapshot_id": "snapshot-test"},
        },
    }
