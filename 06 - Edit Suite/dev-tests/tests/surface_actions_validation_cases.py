from __future__ import annotations

from edit_suite.ui import rendering
from edit_suite.ui import surface as ui_surface
from surface_actions_support import FormWidget, JsonWidget, app, surface


def test_register_action_widget_ignores_preview_duplicate_surface_id() -> None:
    source_surface = surface("optimizer.settings", editor_kind="form")
    preview_surface = surface(
        "optimizer.settings",
        editor_kind="preview_result",
        editable=False,
        value={"descriptor": {}, "current": {}, "draft": {}, "diff": "No drift."},
        draft={},
    )

    widgets: dict[str, dict] = {}
    source_card = {"editor": "source"}
    preview_card = {"editor": "preview"}

    rendering._register_action_widget(widgets, source_surface, source_card)
    rendering._register_action_widget(widgets, preview_surface, preview_card)

    assert widgets == {"optimizer.settings": source_card}


def test_validate_surface_keeps_typed_form_value_on_contract_error(monkeypatch) -> None:
    settings_surface = surface("optimizer.settings", editor_kind="form")
    edit_app, module_entry = app(settings_surface, FormWidget({"parallel_workers": "1", "plugin_timeout_seconds": "120"}))

    def fake_validate(_entry, _draft, *, state_root):
        del state_root
        raise ValueError("config.yaml contains unknown fields: current, descriptor, diff, draft")

    monkeypatch.setattr(ui_surface, "validate_draft", fake_validate)

    edit_app.validate_surface(settings_surface.surface_id)
    updated = edit_app._drafts[module_entry.slot_name][settings_surface.surface_id]

    assert updated.value == {"parallel_workers": "1", "plugin_timeout_seconds": "120"}
    assert updated.dirty is True
    assert updated.message.startswith("Error:")
    assert "descriptor" not in updated.value


def test_apply_surface_action_keeps_last_good_draft_on_json_read_error() -> None:
    preview_surface = surface(
        "optimizer.output_contract_preview",
        editor_kind="json",
        value={"schema_version": "optimizer_raw_v2", "extract_response_paths": []},
        draft={"schema_version": "optimizer_raw_v2", "extract_response_paths": []},
    )
    widget = JsonWidget("[1, 2, 3]")
    edit_app, module_entry = app(preview_surface, widget)

    def unexpected_action(*_args, **_kwargs):
        raise AssertionError("action should not run when widget parsing fails")

    edit_app._apply_surface_action(preview_surface.surface_id, unexpected_action)
    updated = edit_app._drafts[module_entry.slot_name][preview_surface.surface_id]

    assert widget.calls == 1
    assert updated.value == preview_surface.draft
    assert updated.dirty is True
    assert updated.message == "Error: Editor must contain a JSON object."


def test_save_surface_reloads_bundle_before_render(monkeypatch) -> None:
    settings_surface = surface("optimizer.settings", editor_kind="form")
    edit_app, module_entry = app(settings_surface, FormWidget({"parallel_workers": "1"}))
    edit_app._bundles[module_entry.slot_name] = "stale"
    events: list[tuple[str, object]] = []

    def fake_write(_entry, draft, *, state_root):
        del state_root
        events.append(("write", draft.value))
        return ui_surface.DraftState(surface_id=draft.surface_id, value={"parallel_workers": 1}, dirty=False, message="Saved")

    def fake_ensure(reload_entry) -> None:
        events.append(("ensure", reload_entry.slot_name in edit_app._bundles))
        edit_app._bundles[reload_entry.slot_name] = "fresh"

    def fake_render() -> None:
        events.append(("render", edit_app._bundles.get(module_entry.slot_name)))

    monkeypatch.setattr(ui_surface, "write_draft", fake_write)
    edit_app._ensure_bundle = fake_ensure
    edit_app._render = fake_render

    edit_app.save_surface(settings_surface.surface_id)
    updated = edit_app._drafts[module_entry.slot_name][settings_surface.surface_id]

    assert events == [("write", {"parallel_workers": "1"}), ("ensure", False), ("render", "fresh")]
    assert updated.value == {"parallel_workers": 1}
    assert updated.dirty is False
    assert updated.message == "Saved"
