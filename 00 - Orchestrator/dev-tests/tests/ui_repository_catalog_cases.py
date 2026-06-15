from __future__ import annotations

from orchestrator.model_catalog import ModelCatalogGroup, ModelCatalogState
from orchestrator.ui import repository

from .ui_repository_support import _make_app


def test_catalog_models_for_section_ignores_stale_provider_group(tmp_path) -> None:
    app = _make_app(tmp_path)
    app._provider_runtime_widgets["llm_shared"]["provider"].delete(0, "end")
    app._provider_runtime_widgets["llm_shared"]["provider"].insert(0, "Anthropic")
    app._provider_runtime_widgets["llm_shared"]["base_url"].delete(0, "end")
    app._provider_runtime_widgets["llm_shared"]["base_url"].insert(0, "https://api.anthropic.com/v1")
    app._model_catalog_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(
            models=("gpt-5.4", "gpt-5.4-mini"),
            refreshed_at="now",
            source="shared_llm_api_key",
            provider_id="openai",
            base_url="https://api.openai.com/v1",
        ),
    )

    assert repository.catalog_models_for_section(app, "interpreter") == ()


def test_resolve_catalog_model_for_section_maps_unique_provider_alias(tmp_path) -> None:
    app = _make_app(tmp_path)
    app._provider_runtime_widgets["llm_shared"]["provider"].delete(0, "end")
    app._provider_runtime_widgets["llm_shared"]["provider"].insert(0, "OpenRouter")
    app._provider_runtime_widgets["llm_shared"]["base_url"].delete(0, "end")
    app._provider_runtime_widgets["llm_shared"]["base_url"].insert(0, "https://openrouter.ai/api/v1")
    app._model_catalog_state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(
            models=("openai/gpt-5.4", "openai/gpt-5.4-mini"),
            refreshed_at="now",
            source="shared_llm_api_key",
            provider_id="openrouter",
            base_url="https://openrouter.ai/api/v1",
        ),
    )

    assert repository.resolve_catalog_model_for_section(app, "interpreter", "gpt-5.4") == "openai/gpt-5.4"
