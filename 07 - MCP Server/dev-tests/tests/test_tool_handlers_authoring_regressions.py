from __future__ import annotations

from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import ToolFailure, call_tool


@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("derive_working_release_from_blueprint", {"blueprint_ref": "default"}, "artifact_folder fehlt"),
        ("derive_working_release_from_blueprint", {"artifact_folder": "x"}, "blueprint_ref fehlt"),
        ("create_projection_draft", {"artifact_folder": "x", "projection_id": "p"}, "template_projection_id fehlt"),
        ("create_locale_scaffold", {"artifact_folder": "x", "source_locale": "de"}, "target_locale fehlt"),
        (
            "translate_working_release_locale",
            {"source_locale": "de", "target_locale": "en", "translation_payload": {}},
            "artifact_folder fehlt",
        ),
        (
            "translate_working_release_locale",
            {"artifact_folder": "x", "source_locale": "de", "target_locale": "en"},
            "translation_payload fehlt",
        ),
    ],
)
def test_authoring_tools_reject_missing_fields_before_owner_call(
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
