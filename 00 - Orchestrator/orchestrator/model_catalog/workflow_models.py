"""Model catalog seed, filtering, and provider-match helpers."""

from __future__ import annotations

from ..models import ProviderEndpointSettings, RuntimeSettingsState
from .types import ModelCatalogGroup

_LEGACY_OPENAI_PROVIDER_ID = "openai"
_LEGACY_OPENAI_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_LLM_SEED_MODELS = (
    "gpt-5.5-pro",
    "gpt-5.5",
    "gpt-5.5-mini",
    "gpt-5.5-nano",
    "gpt-5.4-pro",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.2-pro",
    "gpt-5.2",
    "gpt-5.2-mini",
    "gpt-5.2-nano",
    "gpt-5.1",
    "gpt-5.1-mini",
    "gpt-5.1-nano",
    "gpt-5-pro",
    "gpt-5",
    "gpt-5-chat-latest",
    "gpt-5-mini",
    "gpt-5-nano",
)
_DEFAULT_EMBEDDING_SEED_MODELS = (
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
)


def seed_models(runtime_settings: RuntimeSettingsState, target: str) -> tuple[str, ...]:
    if target == "llm_shared":
        models = (
            runtime_settings.interpreter.model,
            runtime_settings.normalizer.model,
            *_DEFAULT_LLM_SEED_MODELS,
        )
    elif target == "optimizer_ocr":
        models = (runtime_settings.optimizer_ocr.model, *_DEFAULT_LLM_SEED_MODELS)
    else:
        models = (runtime_settings.corpus_builder_embeddings.model, *_DEFAULT_EMBEDDING_SEED_MODELS)
    seen: set[str] = set()
    seeded: list[str] = []
    for model in models:
        value = str(model or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        seeded.append(value)
    return tuple(seeded)


def classify_models(raw_models: tuple[str, ...], target: str) -> tuple[str, ...]:
    accepted: list[str] = []
    for model in sorted(raw_models):
        lowered = model.lower()
        is_embedding = "embedding" in lowered
        if target == "embeddings" and is_embedding:
            accepted.append(model)
        if target in {"llm_shared", "optimizer_ocr"} and not is_embedding:
            accepted.append(model)
    if accepted:
        return tuple(accepted)
    return tuple(sorted(raw_models))


def group_matches_provider(group: ModelCatalogGroup, provider_settings: ProviderEndpointSettings) -> bool:
    group_provider_id = str(group.provider_id or "").strip()
    group_base_url = str(group.base_url or "").strip().rstrip("/")
    if not group_provider_id and not group_base_url:
        return (
            provider_settings.normalized_provider_id() == _LEGACY_OPENAI_PROVIDER_ID
            and provider_settings.normalized_base_url() == _LEGACY_OPENAI_BASE_URL
        )
    return (
        group_provider_id == provider_settings.normalized_provider_id()
        and group_base_url == provider_settings.normalized_base_url()
    )
