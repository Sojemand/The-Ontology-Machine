from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from edit_suite.surfaces import DraftState
from edit_suite.ui import layout, operation_results, rendering, surface as ui_surface, surface_cards
from edit_suite.ui.view_model import ModuleListItem

from button_evidence_support import entry, invoke, surface, tk_root


def test_shell_refresh_and_open_buttons_invoke_real_commands(tk_root) -> None:
    events: list[tuple[str, str]] = []
    tk_root.refresh_registry = lambda: events.append(("refresh", "registry"))
    shell = layout.build_shell(tk_root, on_tab_change=lambda: events.append(("tab", "changed")))

    invoke(shell["sidebar"], "Refresh Registry")

    rows = rendering.render_module_list(
        shell["module_scroll"],
        {},
        (
            ModuleListItem("01 - Optimizer", "Optimizer", "", "ready"),
            ModuleListItem("04 - Normalizer", "Normalizer", "Contract ready", "ready"),
        ),
        selected_key="01 - Optimizer",
        select_module=lambda key: events.append(("open", key)),
    )
    shell["module_scroll"].update()
    invoke(rows["01 - Optimizer"], "Open")
    invoke(rows["04 - Normalizer"], "Open")

    assert events == [
        ("refresh", "registry"),
        ("open", "01 - Optimizer"),
        ("open", "04 - Normalizer"),
    ]


def test_rendered_validate_and_save_buttons_read_current_widget_value(monkeypatch, tmp_path: Path, tk_root) -> None:
    model = surface()
    module_entry = entry(module_root=str(tmp_path))
    app = object.__new__(ui_surface.EditSuiteApp)
    app._selected_module = module_entry.slot_name
    app._state_root = tmp_path / "state"
    app._drafts = {}
    app._bundles = {}
    app._bundle_errors = {}
    app._request_tokens = {}
    app._surface_action_loading = set()
    app._operation_action_loading = set()
    app._bundle_loading = set()
    app._operation_results = {}
    app._selected_entry = lambda: module_entry
    app._render = lambda: None
    app._ensure_bundle = lambda _entry: None
    app._evict_bundle = lambda _entry: None
    app.action_button_state = lambda _surface_id: "normal"
    app.operation_result_text = lambda _surface_id: ""

    captured: list[tuple[str, dict]] = []

    def fake_validate(_entry, draft, *, state_root):
        del state_root
        captured.append(("validate", dict(draft.value)))
        return DraftState(draft.surface_id, dict(draft.value), dirty=True, message="Valid")

    def fake_write(_entry, draft, *, state_root):
        del state_root
        captured.append(("save", dict(draft.value)))
        return DraftState(draft.surface_id, dict(draft.value), dirty=False, message="Saved")

    monkeypatch.setattr(ui_surface, "validate_draft", fake_validate)
    monkeypatch.setattr(ui_surface, "write_draft", fake_write)

    rendered = surface_cards.render_surface_card(tk_root, model, app=app, row=0)
    app._action_widgets = {model.surface_id: rendered}
    editor = rendered["editor"]
    editor._entries["parallel_workers"].delete(0, "end")
    editor._entries["parallel_workers"].insert(0, "7")
    editor._form_fields["enabled"]["widget"].deselect()

    invoke(tk_root, "Validate")
    invoke(tk_root, "Save")

    assert captured == [
        ("validate", {"parallel_workers": 7, "enabled": False}),
        ("save", {"parallel_workers": 7, "enabled": False}),
    ]
    assert app._drafts[module_entry.slot_name][model.surface_id].dirty is False
    assert app._drafts[module_entry.slot_name][model.surface_id].message == "Saved"


def test_rendered_surface_action_and_merge_choice_buttons_call_expected_workflows(tk_root) -> None:
    events: list[tuple[str, object]] = []
    action_surface = surface(
        descriptor={"action_buttons": [{"action": "audit", "label": "Run Audit", "fixed_payload": {"mode": "quick"}}]},
    )
    app = SimpleNamespace(
        action_button_state=lambda _surface_id: "normal",
        operation_result_text=lambda _surface_id: "",
        validate_surface=lambda surface_id: events.append(("validate", surface_id)),
        save_surface=lambda surface_id: events.append(("save", surface_id)),
        run_surface_action=lambda surface_id, link: events.append(("action", surface_id, link)),
        resolve_merge_interaction=lambda surface_id, choice_id: events.append(("merge", surface_id, choice_id)),
        _operation_results={},
    )

    surface_cards.render_surface_card(tk_root, action_surface, app=app, row=0)
    invoke(tk_root, "Run Audit")

    merge_surface = surface(surface_id="normalizer.merge", editable=False, editor_kind="readonly", value={}, draft={})
    app._operation_results[merge_surface.surface_id] = {
        "label": "Merge Corpus DBs",
        "response": {"status": "ok"},
        "merge_flow": {
            "pending_index": 0,
            "artifact_paths": {},
            "pending_interactions": [
                {
                    "headline": "Confirm merge",
                    "choices": [
                        {"choice_id": "cancel", "label": "Cancel", "decision": None},
                        {"choice_id": "confirm", "label": "Confirm", "decision": "merge_anyway"},
                    ],
                }
            ],
        },
    }
    app.operation_result_text = lambda surface_id: operation_results.result_text(app, surface_id)
    surface_cards.render_surface_card(tk_root, merge_surface, app=app, row=1)
    invoke(tk_root, "Confirm")

    assert events == [
        ("action", action_surface.surface_id, {"action": "audit", "label": "Run Audit", "fixed_payload": {"mode": "quick"}}),
        ("merge", merge_surface.surface_id, "confirm"),
    ]
