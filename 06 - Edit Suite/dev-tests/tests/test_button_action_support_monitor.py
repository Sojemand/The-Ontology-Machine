from __future__ import annotations

from types import SimpleNamespace

from edit_suite.ui import action_forms, support_monitor_editor

from button_evidence_support import entry, invoke, surface, tk_root


def test_action_form_browse_and_support_monitor_buttons_invoke_payload_builders(monkeypatch, tk_root) -> None:
    model = surface(
        surface_id="corpus.search",
        editor_kind="operation",
        editable=False,
        value={},
        draft={},
        operation_links=(
            {
                "action": "search",
                "inputs": [{"name": "input_path", "label": "Input", "field_type": "open_file", "required": True}],
            },
        ),
    )
    module_entry = entry(module_root="C:/Corpus")
    app = SimpleNamespace(_selected_module=module_entry.slot_name, _ui_state={"operation_contexts": {}}, _selected_entry=lambda: module_entry)
    called = {}

    def fake_choose_path(app_arg, entry_widget, field_type, *, spec, widgets, filedialog):
        del filedialog
        called["browse"] = (app_arg, field_type, spec["name"], sorted(widgets))
        entry_widget.delete(0, "end")
        entry_widget.insert(0, "C:/Corpus/input.json")

    monkeypatch.setattr(action_forms.action_path_dialogs, "choose_path", fake_choose_path)
    editor = action_forms.render_action_editor(tk_root, model, app=app)
    editor.grid(row=0, column=0)

    invoke(editor, "Browse")

    assert called["browse"] == (app, "open_file", "input_path", ["input_path"])
    assert editor._action_inputs["input_path"]["widget"].get() == "C:/Corpus/input.json"

    support_surface = surface(
        surface_id="mcp.support",
        editor_kind="support_monitor",
        editable=False,
        value={
            "active_incident_count": 1,
            "event_count": 2,
            "recent_incidents": [
                {
                    "incident_id": "incident-1",
                    "module_key": "mcp_server",
                    "action": "tool_call",
                    "message": "Tool failed",
                }
            ],
        },
        draft={},
    )
    actions: list[dict] = []
    support_app = SimpleNamespace(
        action_button_state=lambda _surface_id: "normal",
        run_surface_action=lambda _surface_id, link: actions.append(link),
    )
    support = support_monitor_editor.render(tk_root, support_surface, app=support_app)
    support.grid(row=1, column=0)

    invoke(support, "Assess")
    invoke(support, "Dismiss")

    assert [item["fixed_payload"]["workflow_action"] for item in actions] == ["assess", "dismiss"]
    assert {item["fixed_payload"]["incident_id"] for item in actions} == {"incident-1"}
