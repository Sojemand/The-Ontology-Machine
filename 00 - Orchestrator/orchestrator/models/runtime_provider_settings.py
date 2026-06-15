"""Provider endpoint settings for orchestrator runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coercion import coerce_str
from .provider_catalog import normalize_provider_id, provider_definition


_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass
class ProviderEndpointSettings:
    provider_id: str = "openai"
    base_url: str = _DEFAULT_OPENAI_BASE_URL

    def validate(self, *, label: str) -> None:
        provider_id = self.normalized_provider_id()
        definition = provider_definition(provider_id)
        if not definition.provider_id:
            raise ValueError(f"{label}: provider_id is invalid.")
        if not self.base_url.strip():
            raise ValueError(f"{label}: base_url must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        self.validate(label="Provider")
        return {
            "provider_id": normalize_provider_id(self.provider_id),
            "base_url": self.base_url.rstrip("/"),
        }

    def normalized_provider_id(self) -> str:
        return normalize_provider_id(self.provider_id)

    def normalized_provider_family(self) -> str:
        return provider_definition(self.provider_id).family

    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")

    def display_name(self) -> str:
        return provider_definition(self.provider_id).display_name

    def supports_llm(self) -> bool:
        return provider_definition(self.provider_id).llm_enabled

    def supports_embeddings(self) -> bool:
        return provider_definition(self.provider_id).embeddings_enabled

    def api_key_is_optional(self) -> bool:
        return provider_definition(self.provider_id).api_key_optional

    def oauth_supported(self) -> bool:
        return provider_definition(self.provider_id).oauth_supported

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        default_provider_id: str = "openai",
        default_base_url: str = _DEFAULT_OPENAI_BASE_URL,
    ) -> "ProviderEndpointSettings":
        payload = data if isinstance(data, dict) else {}
        provider_id = normalize_provider_id(payload.get("provider_id"), default=default_provider_id)
        base_url = coerce_str(payload.get("base_url", default_base_url), default_base_url).strip() or default_base_url
        return cls(provider_id=provider_id, base_url=base_url.rstrip("/"))


def default_llm_shared_provider_settings() -> ProviderEndpointSettings:
    return ProviderEndpointSettings(provider_id="openai", base_url=_DEFAULT_OPENAI_BASE_URL)


def default_embeddings_provider_settings() -> ProviderEndpointSettings:
    return ProviderEndpointSettings(provider_id="openai", base_url=_DEFAULT_OPENAI_BASE_URL)


def default_optimizer_ocr_provider_settings() -> ProviderEndpointSettings:
    return ProviderEndpointSettings(provider_id="openai", base_url=_DEFAULT_OPENAI_BASE_URL)
