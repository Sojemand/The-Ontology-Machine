from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.models import UiState
from orchestrator.ui import repository, workflow


class _EntryStub:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def delete(self, *_args) -> None:
        self.value = ""

    def insert(self, *_args) -> None:
        self.value = str(_args[-1])


class _VarStub:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


def test_create_artifact_tree_bootstraps_tree_fields_without_touching_release_override(monkeypatch, tmp_path: Path) -> None:
    logs: list[str] = []
    events: list[str] = []
    release_override = "C:/external/release.semantic_release.json"
    release_mode = _VarStub("Override Release")
    app = SimpleNamespace(
        _processing=False,
        _ui_state=UiState(semantic_release_path=release_override),
        _input_entry=_EntryStub(),
        _artifact_entry=_EntryStub(),
        _corpus_entry=_EntryStub(),
        _selected_db_entry=_EntryStub(),
        _release_entry=_EntryStub(release_override),
        _mode_var=_VarStub("batch"),
        _semantic_release_mode_var=release_mode,
        _semantic_release_mode_selector=release_mode,
        _flush_pending_saves=lambda: events.append("flush"),
        _append_log=lambda line: logs.append(line),
        _refresh_database_status=lambda: events.append("refresh_database_status"),
        _update_button_state=lambda: events.append("update_button_state"),
        _on_ui_change=lambda: events.append("ui_change"),
    )
    app._save_ui_state = lambda: setattr(app, "_saved_ui_state", repository.current_ui_state(app))
    monkeypatch.setattr(
        workflow.dialogs,
        "prompt_create_artifact_tree",
        lambda _app, **_kwargs: {
            "artifact_root_parent": str(tmp_path),
            "artifact_root_name": "Customer Tree",
        },
    )

    workflow.create_artifact_tree(app)

    root = (tmp_path / "Customer Tree").resolve(strict=False)
    assert app._input_entry.get() == str(root / "Input")
    assert app._artifact_entry.get() == str(root)
    assert app._corpus_entry.get() == str(root / "Corpus")
    assert app._selected_db_entry.get() == str(root / "Corpus" / "corpus.db")
    assert app._release_entry.get() == release_override
    assert app._semantic_release_mode_selector.get() == "DB Release"
    assert app._saved_ui_state.semantic_release_path == release_override
    assert app._saved_ui_state.semantic_release_mode == "database_default"
    assert (root / "Semantic Release").is_dir()
    assert any("Artifact Tree ready" in line for line in logs)
