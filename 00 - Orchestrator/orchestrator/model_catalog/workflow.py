"""Workflow stage for seeded and provider-refreshed model catalogs."""

from __future__ import annotations

from ..models import ProviderEndpointSettings, RuntimeSettingsState, utc_now_iso
from . import adapter
from .types import CatalogRefreshResult, GroupRefreshResult, ModelCatalogGroup, ModelCatalogState
from .workflow_models import classify_models, group_matches_provider, seed_models

_TARGETS = ("llm_shared", "optimizer_ocr", "embeddings")
_LLM_SOURCE = "llm_shared_provider"
_OPTIMIZER_OCR_SOURCE = "optimizer_ocr_provider"
_EMBEDDING_SOURCE = "embeddings_provider"
_TARGET_LABELS = {
    "llm_shared": "LLM Shared API",
    "optimizer_ocr": "Optimizer OCR API",
    "embeddings": "Embeddings API",
}


def effective_model_catalog_state(state: ModelCatalogState, runtime_settings: RuntimeSettingsState) -> ModelCatalogState:
    effective = ModelCatalogState.from_dict(state.to_dict())
    for target in _TARGETS:
        provider_settings = runtime_settings.provider_settings_for_target(target)
        group = effective.group_for(target, provider_settings=provider_settings)
        if group.models and group_matches_provider(group, provider_settings):
            effective.replace_group(target, group)
            continue
        effective.replace_group(
            target,
            ModelCatalogGroup(
                models=seed_models(runtime_settings, target),
                source="runtime_settings_seed",
                provider_id=provider_settings.normalized_provider_id(),
                base_url=provider_settings.normalized_base_url(),
            ),
        )
    return effective


def refresh_model_catalogs(
    current_state: ModelCatalogState,
    *,
    llm_shared_provider: ProviderEndpointSettings,
    optimizer_ocr_provider: ProviderEndpointSettings,
    embeddings_provider: ProviderEndpointSettings,
    shared_llm_api_key: str | None,
    optimizer_ocr_api_key: str | None,
    embeddings_api_key: str | None,
) -> CatalogRefreshResult:
    state = ModelCatalogState.from_dict(current_state.to_dict())
    group_results: dict[str, GroupRefreshResult] = {}
    resolved_embeddings_api_key = _resolved_embeddings_catalog_api_key(
        embeddings_provider=embeddings_provider,
        embeddings_api_key=embeddings_api_key,
        llm_shared_provider=llm_shared_provider,
        shared_llm_api_key=shared_llm_api_key,
    )
    for target, provider_settings, api_key, source in (
        ("llm_shared", llm_shared_provider, shared_llm_api_key, _LLM_SOURCE),
        ("optimizer_ocr", optimizer_ocr_provider, optimizer_ocr_api_key, _OPTIMIZER_OCR_SOURCE),
        ("embeddings", embeddings_provider, resolved_embeddings_api_key, _EMBEDDING_SOURCE),
    ):
        existing = state.group_for(target, provider_settings=provider_settings)
        base_url = provider_settings.normalized_base_url()
        key = str(api_key or "").strip() or None
        if key is None and not provider_settings.api_key_is_optional():
            group_results[target] = GroupRefreshResult(
                target=target,
                status="cached",
                message=_missing_catalog_api_key_message(
                    target,
                    provider_settings=provider_settings,
                    has_existing_catalog=bool(existing.models),
                ),
            )
            continue
        try:
            raw_models = adapter.list_model_ids(provider_settings=provider_settings, api_key=key)
            models = classify_models(raw_models, target)
            if not models:
                raise RuntimeError("Provider returned no matching models for this group.")
            state.replace_group(
                target,
                ModelCatalogGroup(
                    models=models,
                    refreshed_at=utc_now_iso(),
                    source=source,
                    provider_id=provider_settings.normalized_provider_id(),
                    base_url=base_url,
                ),
            )
            group_results[target] = GroupRefreshResult(
                target=target,
                status="updated",
                message=f"{len(models)} models imported from {base_url}/models.",
            )
        except Exception as exc:
            group_results[target] = GroupRefreshResult(
                target=target,
                status="error",
                message=f"{exc}. Previous catalog remains active." if existing.models else str(exc),
            )
    return CatalogRefreshResult(state=state, group_results=group_results)


def _missing_catalog_api_key_message(
    target: str,
    *,
    provider_settings: ProviderEndpointSettings,
    has_existing_catalog: bool,
) -> str:
    fallback = "Previous catalog remains active." if has_existing_catalog else "Runtime settings seed remains active."
    if provider_settings.oauth_supported() and target in {"llm_shared", "optimizer_ocr"}:
        return f"OpenAI OAuth active; live model list requires an API key, using cache/seed for LLM catalogs. {fallback}"
    if target == "embeddings":
        return f"Embedding model list requires an Embeddings API key, using cache/seed. {fallback}"
    return f"Provider model list requires a stored {_TARGET_LABELS.get(target, target)} key, using cache/seed. {fallback}"


def _resolved_embeddings_catalog_api_key(
    *,
    embeddings_provider: ProviderEndpointSettings,
    embeddings_api_key: str | None,
    llm_shared_provider: ProviderEndpointSettings,
    shared_llm_api_key: str | None,
) -> str | None:
    explicit = str(embeddings_api_key or "").strip()
    if explicit:
        return explicit
    fallback = str(shared_llm_api_key or "").strip()
    if not fallback:
        return None
    if _providers_share_catalog_access(embeddings_provider, llm_shared_provider):
        return fallback
    return None


def _providers_share_catalog_access(
    left: ProviderEndpointSettings,
    right: ProviderEndpointSettings,
) -> bool:
    return (
        left.normalized_base_url() == right.normalized_base_url()
        or (
            left.normalized_provider_id() == right.normalized_provider_id()
            and left.normalized_provider_family() == right.normalized_provider_family()
        )
    )
