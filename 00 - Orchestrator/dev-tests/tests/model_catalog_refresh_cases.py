from __future__ import annotations

from orchestrator.model_catalog import ModelCatalogGroup, ModelCatalogState, refresh_model_catalogs
from orchestrator.models import ProviderEndpointSettings


def test_refresh_model_catalogs_updates_only_successful_groups(monkeypatch) -> None:
    calls: list[tuple[str, str, str | None]] = []

    def fake_list_model_ids(*, provider_settings, api_key: str | None = None, timeout: int = 15) -> tuple[str, ...]:
        _ = timeout
        calls.append((provider_settings.provider_id, provider_settings.base_url, api_key))
        if api_key in {"shared-key", "ocr-key"}:
            return ("gpt-5.4", "gpt-5.4-mini", "text-embedding-3-small")
        raise RuntimeError("Embeddings /models failed")

    monkeypatch.setattr("orchestrator.model_catalog.workflow.adapter.list_model_ids", fake_list_model_ids)

    result = refresh_model_catalogs(
        ModelCatalogState(embeddings=ModelCatalogGroup(models=("text-embedding-3-small",), refreshed_at="old", source="embeddings_api_key")),
        llm_shared_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        optimizer_ocr_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        embeddings_provider=ProviderEndpointSettings(provider_id="openai_compat", base_url="http://127.0.0.1:1234/v1"),
        shared_llm_api_key="shared-key",
        optimizer_ocr_api_key="ocr-key",
        embeddings_api_key="embed-key",
    )

    assert calls == [
        ("openai", "https://api.openai.com/v1", "shared-key"),
        ("openai", "https://api.openai.com/v1", "ocr-key"),
        ("openai_compat", "http://127.0.0.1:1234/v1", "embed-key"),
    ]
    assert result.state.llm_shared.models == ("gpt-5.4", "gpt-5.4-mini")
    assert result.state.optimizer_ocr.models == ("gpt-5.4", "gpt-5.4-mini")
    assert result.state.embeddings.models == ("text-embedding-3-small",)
    assert result.group_results["llm_shared"].status == "updated"
    assert result.group_results["optimizer_ocr"].status == "updated"
    assert result.group_results["embeddings"].status == "error"


def test_refresh_model_catalogs_skips_openai_catalog_without_api_key(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_list_model_ids(*, provider_settings, api_key: str | None = None, timeout: int = 15) -> tuple[str, ...]:
        _ = timeout
        calls.append((provider_settings.provider_id, api_key))
        if api_key == "embed-key":
            return ("gpt-5.4", "text-embedding-3-small")
        raise AssertionError("OpenAI /models must not be called without an API key")

    monkeypatch.setattr("orchestrator.model_catalog.workflow.adapter.list_model_ids", fake_list_model_ids)

    result = refresh_model_catalogs(
        ModelCatalogState(
            llm_shared=ModelCatalogGroup(
                models=("gpt-cached",),
                refreshed_at="old",
                source="llm_shared_provider",
                provider_id="openai",
                base_url="https://api.openai.com/v1",
            )
        ),
        llm_shared_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        optimizer_ocr_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        embeddings_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        shared_llm_api_key=None,
        optimizer_ocr_api_key=None,
        embeddings_api_key="embed-key",
    )

    assert calls == [("openai", "embed-key")]
    assert result.state.llm_shared.models == ("gpt-cached",)
    assert result.state.optimizer_ocr.models == ()
    assert result.state.embeddings.models == ("text-embedding-3-small",)
    assert result.group_results["llm_shared"].status == "cached"
    assert "OpenAI OAuth active" in result.group_results["llm_shared"].message
    assert result.group_results["optimizer_ocr"].status == "cached"
    assert result.group_results["embeddings"].status == "updated"


def test_refresh_model_catalogs_reuses_shared_key_for_matching_embeddings_provider(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_list_model_ids(*, provider_settings, api_key: str | None = None, timeout: int = 15) -> tuple[str, ...]:
        _ = timeout
        calls.append((provider_settings.provider_id, api_key))
        if provider_settings.provider_id == "openai":
            return ("gpt-5.4", "text-embedding-3-small")
        raise AssertionError("unexpected provider")

    monkeypatch.setattr("orchestrator.model_catalog.workflow.adapter.list_model_ids", fake_list_model_ids)

    result = refresh_model_catalogs(
        ModelCatalogState(),
        llm_shared_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        optimizer_ocr_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        embeddings_provider=ProviderEndpointSettings(provider_id="openai", base_url="https://api.openai.com/v1"),
        shared_llm_api_key="shared-key",
        optimizer_ocr_api_key="ocr-key",
        embeddings_api_key=None,
    )

    assert calls == [("openai", "shared-key"), ("openai", "ocr-key"), ("openai", "shared-key")]
    assert result.state.optimizer_ocr.models == ("gpt-5.4",)
    assert result.state.embeddings.models == ("text-embedding-3-small",)
    assert result.group_results["embeddings"].status == "updated"
