from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_payload"),
    [
        (
            "derive_working_release_from_blueprint",
            {"blueprint_ref": "default", "target_release_id": "semantic_release.default"},
            {
                "action": "derive_working_release_from_blueprint",
                "blueprint_ref": "default",
                "target_release_id": "semantic_release.default",
            },
        ),
        (
            "create_minimal_custom_release",
            {
                "language": "de",
                "projection_id": "fantasy.story.custom.v1",
                "archive_label": "Fantasy",
                "archive_description": "Small fantasy archive.",
                "document_types": [{"code": "story", "label": "Story", "description": "Story."}],
                "field_codes": [{"code": "character", "label": "Character", "description": "Character."}],
            },
            {
                "action": "create_minimal_custom_release",
                "language": "de",
                "release_id": "semantic_release.fantasy.story.custom.v1",
                "projection_id": "fantasy.story.custom.v1",
                "archive_label": "Fantasy",
                "archive_description": "Small fantasy archive.",
                "document_types": [{"code": "story", "label": "Story", "description": "Story."}],
                "field_codes": [{"code": "character", "label": "Character", "description": "Character."}],
            },
        ),
        (
            "create_projection_draft",
            {
                "projection_id": "fantasy.story.default.v1",
                "template_projection_id": "personal.expression.default.v1",
                "language": "de",
                "label": "Fantasy",
                "description": "Story profile.",
                "when_to_use": "Story documents.",
                "avoid_when": "Other documents.",
                "example_document_types": "story",
                "domain_ids": "personal",
                "include_document_types": "other",
                "include_categories": "personal",
                "include_subcategories": "other",
                "include_field_codes": "subject",
                "include_row_types": "other",
                "include_cell_codes": "note",
            },
            {
                "action": "create_projection_draft",
                "projection_id": "fantasy.story.default.v1",
                "template_projection_id": "personal.expression.default.v1",
                "locale": "de",
                "label": "Fantasy",
                "description": "Story profile.",
                "when_to_use": "Story documents.",
                "avoid_when": "Other documents.",
                "example_document_types": "story",
                "domain_ids": "personal",
                "include_document_types": "other",
                "include_categories": "personal",
                "include_subcategories": "other",
                "include_field_codes": "subject",
                "include_row_types": "other",
                "include_cell_codes": "note",
            },
        ),
        (
            "generate_locale_translation_payload",
            {"source_language": "de", "target_language": "en", "model": "gpt-test", "max_output_tokens": 1000},
            {
                "action": "generate_locale_translation_payload",
                "source_locale": "de",
                "target_locale": "en",
                "model": "gpt-test",
                "max_output_tokens": 1000,
            },
        ),
        (
            "translate_working_release_locale",
            {
                "source_locale": "de",
                "target_locale": "en",
                "translation_payload": {"master": {}, "projections": {}},
                "overwrite_existing": True,
            },
            {
                "action": "translate_release_locale",
                "source_locale": "de",
                "target_locale": "en",
                "translation_payload": {"master": {}, "projections": {}},
                "overwrite_existing": True,
            },
        ),
    ],
)
def test_authoring_tools_use_one_workspace_normalizer_edit(
    tool_name: str,
    arguments: dict[str, Any],
    expected_payload: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_folder = tmp_path / "workspace"
    calls: list[tuple[str, dict[str, Any], dict[str, str] | None]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload, kwargs.get("env_overrides")))
        return {"status": "ok"}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool(tool_name, {"artifact_folder": str(artifact_folder), **arguments})

    normalizer_home = artifact_folder.resolve() / ".vp" / "n"
    assert result["status"] == "ok"
    assert result["authoring_scope"] == "workspace"
    assert result["normalizer_authoring_home"] == str(normalizer_home)
    assert calls == [("normalizer", expected_payload, {"NORMALIZER_VISION_HOME": str(normalizer_home)})]
    assert not (artifact_folder / "Input").exists()
