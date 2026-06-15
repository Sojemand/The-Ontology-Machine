from __future__ import annotations

from types import SimpleNamespace

from surface_actions_support import PromptBundleWidget, app, surface


def test_read_widget_value_collects_split_prompt_bundle_sections() -> None:
    payload = {
        "system_prompt_md": "  system prompt  ",
        "user_prompt_rules_md": "user prompt",
        "output_schema_json": "{\n  \"type\": \"object\"\n}\n",
        "projection_hint_policy_md": "projection hint",
    }
    prompt_surface = surface("interpreter.prompt_bundle", editor_kind="prompt_bundle", value=payload, draft=payload)
    edit_app, _entry = app(prompt_surface, PromptBundleWidget(payload))

    value = edit_app._read_widget_value(prompt_surface.surface_id)

    assert value == {
        "system_prompt_md": "system prompt",
        "user_prompt_rules_md": "user prompt",
        "output_schema_json": "{\n  \"type\": \"object\"\n}",
        "projection_hint_policy_md": "projection hint",
    }


def test_read_widget_value_supports_taxonomy_release_draft_editor_kind(monkeypatch) -> None:
    from edit_suite.ui import taxonomy_release_editor

    payload = {
        "schema_version": "taxonomy_release_draft.v1",
        "artifact_root": "C:/Artifact Tree",
        "release": {"release_id": "rel.current"},
    }
    release_surface = surface(
        "normalizer.taxonomy_release_draft",
        editor_kind="taxonomy_release_draft",
        value=payload,
        draft=payload,
    )
    release_widget = SimpleNamespace(marker="release-draft")
    edit_app, _entry = app(release_surface, release_widget)

    monkeypatch.setattr(taxonomy_release_editor, "read_value", lambda widget: {**payload, "marker": widget.marker})

    assert edit_app._read_widget_value(release_surface.surface_id) == {
        "schema_version": "taxonomy_release_draft.v1",
        "artifact_root": "C:/Artifact Tree",
        "release": {"release_id": "rel.current"},
        "marker": "release-draft",
    }
