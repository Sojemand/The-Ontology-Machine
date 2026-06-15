from __future__ import annotations

import json
from pathlib import Path

import customtkinter as ctk

from edit_suite.ui import corpus_db_dialog, operation_progress

from button_evidence_support import button, entry, invoke, surface, tk_root, walk


def test_new_corpus_db_dialog_cancel_and_create_buttons_write_confirmation(tmp_path: Path, tk_root) -> None:
    model = surface(surface_id="normalizer.taxonomy_release_draft", draft={"default_runtime_locale": "de"})
    tk_root._state_root = tmp_path / "state"
    tk_root._pipeline_root = ""
    tk_root._selected_module = "04 - Normalizer"
    tk_root._ui_state = {"operation_contexts": {}}
    tk_root._action_widgets = {model.surface_id: {"surface": model}}
    tk_root._selected_entry = lambda: entry(module_root=str(tmp_path))
    action_link = {
        "action": "materialize_corpus_db_from_release",
        "new_corpus_db_dialog": {
            "label_persist_key": "new_corpus_db_label",
            "locale_persist_key": "new_corpus_db_taxonomy_locale",
            "locale_options": ["de", "en"],
        },
    }

    tk_root.after(20, lambda: invoke(tk_root, "Cancel"))
    assert corpus_db_dialog.prompt_new_corpus_db_creation(tk_root, model.surface_id, action_link, {}) is None

    def submit_dialog() -> None:
        entries = [widget for widget in walk(tk_root) if isinstance(widget, ctk.CTkEntry)]
        editable_entries = [item for item in entries if str(item.cget("state")) != "readonly"]
        editable_entries[0].insert(0, "Audit Corpus")
        invoke(tk_root, "Create")

    tk_root.after(20, submit_dialog)
    result = corpus_db_dialog.prompt_new_corpus_db_creation(tk_root, model.surface_id, action_link, {})

    assert result is not None
    artifact_path = Path(result["confirmation_artifact_path"])
    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["database_label"] == "Audit Corpus"
    assert payload["taxonomy_locale"] == "de"
    context = tk_root._ui_state["operation_contexts"][tk_root._selected_module]
    assert context["new_corpus_db_label"] == "Audit Corpus"
    assert context["new_corpus_db_taxonomy_locale"] == "de"


def test_progress_window_close_button_only_closes_after_completion(tk_root) -> None:
    handle = operation_progress.OperationProgressWindow(
        tk_root,
        surface_id="normalizer.long_action",
        title="Long Action",
        status="Running",
    )
    assert str(button(handle.window, "Close").cget("state")) == "disabled"

    handle.complete({"status": "ok", "headline": "Done"})
    assert str(button(handle.window, "Close").cget("state")) == "normal"
    invoke(handle.window, "Close")

    assert operation_progress._windows(tk_root) == {}
