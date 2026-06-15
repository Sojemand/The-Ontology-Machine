from __future__ import annotations

from orchestrator.model_catalog import (
    ModelCatalogGroup,
    ModelCatalogState,
    effective_model_catalog_state,
    list_model_ids,
    refresh_model_catalogs,
)
from orchestrator.models import ProviderEndpointSettings, RuntimeSettingsState, provider_definition


EXPECTED_PROVIDER_FAMILIES = {
    "openai": "openai_responses",
    "anthropic": "anthropic_messages",
    "google": "google_gemini",
    "xai": "openai_responses",
    "openrouter": "openai_chat",
    "groq": "openai_responses",
    "together": "openai_chat",
    "fireworks": "openai_chat",
    "mistral": "openai_chat",
    "deepseek": "openai_chat",
    "sambanova": "openai_chat",
    "cerebras": "openai_chat",
    "mammouth": "openai_chat",
    "lmstudio": "openai_chat",
    "ollama": "openai_chat",
    "openai_compat": "openai_chat",
}


def test_provider_catalog_maps_selectable_providers_to_expected_families() -> None:
    for provider_id, family in EXPECTED_PROVIDER_FAMILIES.items():
        assert provider_definition(provider_id).family == family


def test_openrouter_runtime_family_uses_chat_completions() -> None:
    settings = ProviderEndpointSettings(provider_id="openrouter", base_url="https://openrouter.ai/api/v1")

    assert settings.normalized_provider_family() == EXPECTED_PROVIDER_FAMILIES["openrouter"]


def test_list_model_ids_supports_google_catalog(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator.model_catalog.adapter._read_json",
        lambda _request, *, timeout: {"models": [{"name": "models/gemini-2.5-flash"}, {"name": "models/gemini-embedding-001"}]},
    )

    models = list_model_ids(
        provider_settings=ProviderEndpointSettings(
            provider_id="google",
            base_url="https://generativelanguage.googleapis.com/v1beta",
        ),
        api_key="google-key",
    )

    assert models == ("gemini-2.5-flash", "gemini-embedding-001")


def test_refresh_model_catalogs_keeps_cached_groups_for_multiple_providers(monkeypatch) -> None:
    def fake_list_model_ids(*, provider_settings, api_key: str | None = None, timeout: int = 15) -> tuple[str, ...]:
        _ = api_key, timeout
        if provider_settings.provider_id == "openai":
            return ("gpt-5.4", "gpt-5.4-mini")
        if provider_settings.provider_id == "anthropic":
            return ("claude-sonnet-4", "claude-haiku-4.5")
        raise AssertionError("unexpected provider")

    monkeypatch.setattr("orchestrator.model_catalog.workflow.adapter.list_model_ids", fake_list_model_ids)

    state = refresh_model_catalogs(
        ModelCatalogState(),
        llm_shared_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        optimizer_ocr_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        embeddings_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        shared_llm_api_key="shared-key",
        optimizer_ocr_api_key="ocr-key",
        embeddings_api_key="shared-key",
    ).state

    state = refresh_model_catalogs(
        state,
        llm_shared_provider=ProviderEndpointSettings(provider_id="anthropic", base_url="https://api.anthropic.com/v1"),
        optimizer_ocr_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        embeddings_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        shared_llm_api_key="anthropic-key",
        optimizer_ocr_api_key="ocr-key",
        embeddings_api_key="shared-key",
    ).state

    assert tuple(group.provider_id for group in state.llm_shared_catalogs) == ("anthropic", "openai")
    assert state.group_for(
        "llm_shared",
        provider_settings=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
    ).models == ("gpt-5.4", "gpt-5.4-mini")
    assert state.group_for(
        "llm_shared",
        provider_settings=ProviderEndpointSettings(provider_id="anthropic", base_url="https://api.anthropic.com/v1"),
    ).models == ("claude-haiku-4.5", "claude-sonnet-4")


def test_effective_model_catalog_state_uses_cached_group_for_selected_provider() -> None:
    state = ModelCatalogState(
        llm_shared=ModelCatalogGroup(
            models=("gpt-5.4",),
            refreshed_at="now",
            source="shared_llm_api_key",
            provider_id="openai",
            base_url="https://api.openai.com/v1",
        ),
        llm_shared_catalogs=(
            ModelCatalogGroup(
                models=("claude-sonnet-4",),
                refreshed_at="later",
                source="shared_llm_api_key",
                provider_id="anthropic",
                base_url="https://api.anthropic.com/v1",
            ),
        ),
    )

    effective = effective_model_catalog_state(
        state,
        RuntimeSettingsState.from_dict(
            {
                "schema_version": 1,
                "llm_shared_provider": {
                    "provider_id": "anthropic",
                    "base_url": "https://api.anthropic.com/v1",
                },
                "interpreter": {"model": "gpt-5.4", "max_output_tokens": 8000},
                "normalizer": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
                "corpus_builder_embeddings": {"model": "text-embedding-3-small"},
            }
        ),
    )

    assert effective.llm_shared.provider_id == "anthropic"
    assert effective.llm_shared.models == ("claude-sonnet-4",)


def test_effective_model_catalog_state_reuses_legacy_openai_catalog_without_provider_metadata() -> None:
    effective = effective_model_catalog_state(
        ModelCatalogState(
            llm_shared=ModelCatalogGroup(
                models=("gpt-4.1", "gpt-4.1-mini"),
                refreshed_at="now",
                source="shared_llm_api_key",
            ),
        ),
        RuntimeSettingsState.from_dict(
            {
                "schema_version": 1,
                "llm_shared_provider": {
                    "provider_id": "openai",
                    "base_url": "https://api.openai.com/v1",
                },
                "interpreter": {"model": "gpt-5.4", "max_output_tokens": 8000},
                "normalizer": {"model": "gpt-5.4-mini", "max_output_tokens": 15000},
                "corpus_builder_embeddings": {"model": "text-embedding-3-small"},
            }
        ),
    )

    assert effective.llm_shared.models == ("gpt-4.1", "gpt-4.1-mini")
    assert effective.llm_shared.source == "shared_llm_api_key"
