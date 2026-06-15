from __future__ import annotations

from orchestrator.model_catalog import ModelCatalogGroup, ModelCatalogState
from orchestrator.ui import model_catalog_actions

from .model_catalog_ui_support import _Widget, _app


def test_render_model_catalog_uses_effective_catalog_for_status_badges(monkeypatch) -> None:
    app = _app()
    app._model_catalog_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(models=("gpt-stale",), refreshed_at="old", source="shared_llm_api_key"),
        optimizer_ocr=ModelCatalogGroup(models=("gpt-ocr-stale",), refreshed_at="old", source="optimizer_ocr_api_key"),
        embeddings=ModelCatalogGroup(models=("text-embedding-stale",), refreshed_at="old", source="embeddings_api_key"),
    )

    monkeypatch.setattr(
        "orchestrator.ui.model_catalog_actions.model_catalog.effective_model_catalog_state",
        lambda _state, _runtime: ModelCatalogState(
            llm_shared=ModelCatalogGroup(models=("gpt-5.4", "gpt-5.4-mini"), refreshed_at="now", source="shared_llm_api_key"),
            optimizer_ocr=ModelCatalogGroup(models=("gpt-5.4",), refreshed_at="now", source="optimizer_ocr_api_key"),
            embeddings=ModelCatalogGroup(models=("text-embedding-3-small",), refreshed_at="now", source="embeddings_api_key"),
        ),
    )

    model_catalog_actions.render_model_catalog(app)

    assert app._runtime_settings_widgets["interpreter"]["model_status"].cget("text") == "Provider catalog valid"
    assert app._runtime_settings_widgets["normalizer"]["model_status"].cget("text") == "Provider catalog valid"
    assert app._runtime_settings_widgets["optimizer_ocr"]["model_status"].cget("text") == "Provider catalog valid"
    assert app._runtime_settings_widgets["corpus_builder_embeddings"]["model_status"].cget("text") == "Provider catalog valid"


def test_render_model_catalog_resolves_provider_prefixed_aliases(monkeypatch) -> None:
    app = _app()
    app._provider_runtime_widgets = {
        "llm_shared": {
            "provider": _Widget("OpenRouter"),
            "base_url": _Widget("https://openrouter.ai/api/v1"),
        },
        "optimizer_ocr": {
            "provider": _Widget("OpenRouter"),
            "base_url": _Widget("https://openrouter.ai/api/v1"),
        },
        "embeddings": {
            "provider": _Widget("OpenAI"),
            "base_url": _Widget("https://api.openai.com/v1"),
        },
    }
    app._runtime_settings_widgets["interpreter"]["model"].set("gpt-5.4")
    app._runtime_settings_widgets["normalizer"]["model"].set("gpt-5.4-mini")
    app._runtime_settings_widgets["optimizer_ocr"]["model"].set("gpt-5.4")
    app._model_catalog_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(
            models=("openai/gpt-5.4", "openai/gpt-5.4-mini"),
            refreshed_at="now",
            source="shared_llm_api_key",
            provider_id="openrouter",
            base_url="https://openrouter.ai/api/v1",
        ),
        optimizer_ocr=ModelCatalogGroup(
            models=("openai/gpt-5.4",),
            refreshed_at="now",
            source="optimizer_ocr_api_key",
            provider_id="openrouter",
            base_url="https://openrouter.ai/api/v1",
        ),
        embeddings=ModelCatalogGroup(
            models=("text-embedding-3-small",),
            refreshed_at="now",
            source="embeddings_api_key",
            provider_id="openai",
            base_url="https://api.openai.com/v1",
        ),
    )

    monkeypatch.setattr(
        "orchestrator.ui.model_catalog_actions.model_catalog.effective_model_catalog_state",
        lambda state, _runtime: state,
    )

    model_catalog_actions.render_model_catalog(app)

    assert app._runtime_settings_widgets["interpreter"]["model"].get() == "openai/gpt-5.4"
    assert app._runtime_settings_widgets["normalizer"]["model"].get() == "openai/gpt-5.4-mini"
    assert app._runtime_settings_widgets["optimizer_ocr"]["model"].get() == "openai/gpt-5.4"
    assert app._runtime_settings_widgets["interpreter"]["model_status"].cget("text") == "Provider catalog valid"
    assert app._runtime_settings_widgets["normalizer"]["model_status"].cget("text") == "Provider catalog valid"
    assert app._runtime_settings_widgets["optimizer_ocr"]["model_status"].cget("text") == "Provider catalog valid"
