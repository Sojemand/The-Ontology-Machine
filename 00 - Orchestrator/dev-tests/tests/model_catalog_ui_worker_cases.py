from __future__ import annotations

import threading

from orchestrator.model_catalog import CatalogRefreshResult, GroupRefreshResult, ModelCatalogGroup, ModelCatalogState
from orchestrator.models import RuntimeSettingsState
from orchestrator.ui import model_catalog_actions

from .model_catalog_ui_support import _app


def test_refresh_worker_loads_provider_specific_api_keys(monkeypatch) -> None:
    app = _app()
    app._state_dir = "state-dir"
    calls: list[tuple[str, str]] = []
    runtime_settings = RuntimeSettingsState.from_dict(
        {
            "schema_version": 1,
            "llm_shared_provider": {
                "provider_id": "xai",
                "base_url": "https://api.x.ai/v1",
            },
            "embeddings_provider": {
                "provider_id": "openai",
                "base_url": "https://api.openai.com/v1",
            },
            "optimizer_ocr_provider": {
                "provider_id": "xai",
                "base_url": "https://api.x.ai/v1",
            },
            "interpreter": {"model": "grok-3-beta", "max_output_tokens": 8000},
            "normalizer": {"model": "grok-3-mini", "max_output_tokens": 15000},
            "optimizer_ocr": {"model": "grok-3-beta", "max_output_tokens": 15000, "timeout_seconds": 120},
            "corpus_builder_embeddings": {"model": "text-embedding-3-small"},
        }
    )
    app.after = lambda _delay, callback: callback()

    monkeypatch.setattr(
        "orchestrator.ui.model_catalog_actions.repository.current_runtime_settings",
        lambda _app: runtime_settings,
    )
    monkeypatch.setattr(
        "orchestrator.ui.model_catalog_actions.credentials.load_api_key",
        lambda _state_dir, target, **kwargs: calls.append(
            (target, kwargs["provider_settings"].normalized_provider_id())
        ) or f"{target}-secret",
    )
    monkeypatch.setattr(
        "orchestrator.ui.model_catalog_actions.model_catalog.refresh_model_catalogs",
        lambda *_args, **_kwargs: CatalogRefreshResult(
            state=ModelCatalogState(
                llm_shared=ModelCatalogGroup(
                    models=("grok-3-beta",),
                    refreshed_at="now",
                    source="llm_shared_provider",
                    provider_id="xai",
                    base_url="https://api.x.ai/v1",
                ),
                optimizer_ocr=ModelCatalogGroup(
                    models=("grok-3-beta",),
                    refreshed_at="now",
                    source="optimizer_ocr_provider",
                    provider_id="xai",
                    base_url="https://api.x.ai/v1",
                ),
                embeddings=ModelCatalogGroup(
                    models=("text-embedding-3-small",),
                    refreshed_at="now",
                    source="embeddings_provider",
                    provider_id="openai",
                    base_url="https://api.openai.com/v1",
                ),
            ),
            group_results={
                "llm_shared": GroupRefreshResult("llm_shared", "updated", "llm"),
                "optimizer_ocr": GroupRefreshResult("optimizer_ocr", "updated", "ocr"),
                "embeddings": GroupRefreshResult("embeddings", "updated", "embeddings"),
            },
        ),
    )

    model_catalog_actions._refresh_worker(app, 2)

    assert calls == [("llm_shared", "xai"), ("optimizer_ocr", "xai"), ("embeddings", "openai")]


def test_start_refresh_flushes_runtime_and_syncs_credentials_before_worker(monkeypatch) -> None:
    app = _app()
    app._model_catalog_refreshing = False
    calls: list[str] = []
    app._flush_pending_save = lambda key: calls.append(f"flush:{key}")
    app._refresh_credentials_view = lambda: calls.append("credentials")
    app._credential_widgets = {}
    app._credentials_notice_label = object()
    app.after = lambda _delay, callback: callback()

    class ImmediateThread:
        def __init__(self, *, target, args, daemon):
            self._target = target
            self._args = args
            self.daemon = daemon

        def start(self):
            calls.append("worker")

    monkeypatch.setattr(threading, "Thread", ImmediateThread)

    model_catalog_actions.start_model_catalog_refresh(app)

    assert calls[:3] == ["flush:runtime_settings", "credentials", "worker"]
