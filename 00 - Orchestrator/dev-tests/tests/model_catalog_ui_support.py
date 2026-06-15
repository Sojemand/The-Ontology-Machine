from __future__ import annotations

from types import SimpleNamespace

from orchestrator.model_catalog import ModelCatalogState
from orchestrator.models import RuntimeSettingsState


class _Widget:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.config: dict[str, object] = {}

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value

    def configure(self, **kwargs) -> None:
        self.config.update(kwargs)
        if "text" in kwargs:
            self.value = str(kwargs["text"])

    def cget(self, key: str):
        return self.config.get(key, self.value if key == "text" else None)


def _app() -> SimpleNamespace:
    return SimpleNamespace(
        _model_catalog_request_id=2,
        _model_catalog_refreshing=True,
        _model_catalog_notice_text="",
        _model_catalog_state=ModelCatalogState(),
        _model_catalog_group_labels={"llm_shared": _Widget(), "optimizer_ocr": _Widget(), "embeddings": _Widget()},
        _model_catalog_notice_label=_Widget(),
        _model_catalog_refresh_button=_Widget(),
        _runtime_settings=RuntimeSettingsState(),
        _runtime_settings_widgets={
            "interpreter": {"model": _Widget("gpt-5.4"), "model_status": _Widget()},
            "normalizer": {"model": _Widget("gpt-5.4-mini"), "model_status": _Widget()},
            "optimizer_ocr": {"model": _Widget("gpt-5.4"), "model_status": _Widget()},
            "corpus_builder_embeddings": {"model": _Widget("text-embedding-3-small"), "model_status": _Widget()},
        },
        _update_button_state=lambda: None,
        _state_dir=None,
    )
