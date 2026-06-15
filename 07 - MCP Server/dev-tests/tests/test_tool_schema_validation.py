from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool
from tests.tool_contract_matrix_recorder import OwnerCallRecorder


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("set_runtime_api_key", {"target": "bad", "secret_value": "sk-test"}, "target muss eines"),
        ("delete_runtime_api_key", {"target": "bad"}, "target muss eines"),
        ("reveal_secret", {"target": "bad", "purpose": "test", "unlock_phrase": "unlock"}, "target muss eines"),
        ("search_corpus", {"query": "invoice", "mode": "BAD"}, "mode muss eines"),
        ("export_corpus", {"output_path": "out.jsonl", "fmt": "xml"}, "fmt muss eines"),
    ],
)
def test_catalog_enum_constraints_reject_before_owner_call(
    tool_name: str,
    arguments: dict[str, Any],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = OwnerCallRecorder({})
    recorder.install(monkeypatch)

    with pytest.raises(ToolFailure, match=message):
        call_tool(tool_name, arguments)

    assert recorder.product_calls == []
    assert recorder.edit_calls == []
    assert recorder.admin_calls == []


def test_projection_draft_requires_catalog_filter_fields_before_owner_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(tool_handlers, "_invoke_edit", lambda module_key, payload, **_kwargs: calls.append((module_key, payload)))

    with pytest.raises(ToolFailure, match="domain_ids fehlt"):
        call_tool(
            "create_projection_draft",
            {
                "artifact_folder": "x",
                "projection_id": "fantasy.story.default.v1",
                "template_projection_id": "personal.expression.default.v1",
                "language": "de",
                "label": "Fantasy Story",
                "description": "Profil fuer Story-Notizen.",
                "when_to_use": "Fuer Story-Dokumente.",
                "avoid_when": "Nicht fuer Rechnungen.",
                "example_document_types": "story_notes",
            },
        )

    assert calls == []


def test_read_working_release_does_not_initialize_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact_folder = tmp_path / "workspace"
    calls: list[tuple[str, dict[str, Any], dict[str, str] | None]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], *, env_overrides: dict[str, str] | None = None) -> dict[str, Any]:
        calls.append((module_key, payload, env_overrides))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool("read_working_release", {"artifact_folder": str(artifact_folder)})

    assert result["status"] == "ok"
    assert not artifact_folder.exists()
    assert calls == [
        (
            "normalizer",
            {"action": "read_release_package"},
            {"NORMALIZER_VISION_HOME": str(artifact_folder.resolve() / ".vp" / "n")},
        )
    ]
