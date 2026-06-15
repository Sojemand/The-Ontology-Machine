from __future__ import annotations

from types import SimpleNamespace

from orchestrator.models import RuntimeSettingsState, UiState


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
    def __init__(self, value: str = "batch") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


def _make_app(tmp_path, state: UiState | None = None):
    mode = _VarStub()
    release_mode = _VarStub("DB Release")
    return SimpleNamespace(
        _state_dir=tmp_path / "state",
        _ui_state_path=tmp_path / "ui_state.json",
        _ui_state=state or UiState(),
        _runtime_settings=RuntimeSettingsState(),
        _input_entry=_EntryStub(),
        _artifact_entry=_EntryStub(),
        _release_entry=_EntryStub(),
        _corpus_entry=_EntryStub(),
        _selected_db_entry=_EntryStub(),
        _mode_var=mode,
        _mode_selector=mode,
        _semantic_release_mode_var=release_mode,
        _semantic_release_mode_selector=release_mode,
        _provider_runtime_widgets={
            "llm_shared": {
                "provider": _EntryStub("OpenAI"),
                "base_url": _EntryStub("https://api.openai.com/v1"),
                "note": _EntryStub(),
            },
            "optimizer_ocr": {
                "provider": _EntryStub("OpenAI"),
                "base_url": _EntryStub("https://api.openai.com/v1"),
                "note": _EntryStub(),
            },
            "embeddings": {
                "provider": _EntryStub("OpenAI"),
                "base_url": _EntryStub("https://api.openai.com/v1"),
                "note": _EntryStub(),
            },
        },
        _runtime_settings_widgets={
            "interpreter": {
                "model": _EntryStub(),
                "max_output_tokens": _EntryStub(),
            },
            "normalizer": {
                "model": _EntryStub(),
                "max_output_tokens": _EntryStub(),
            },
            "optimizer_ocr": {
                "model": _EntryStub(),
                "max_output_tokens": _EntryStub(),
                "timeout_seconds": _EntryStub(),
            },
            "corpus_builder_embeddings": {
                "model": _EntryStub(),
            },
        },
        _on_ui_change=lambda: None,
    )
