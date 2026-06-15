"""Group-level model catalog state and matching rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import ProviderEndpointSettings
from .targets import LEGACY_OPENAI_BASE_URL, LEGACY_OPENAI_PROVIDER_ID


def _coerce_models(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    seen: set[str] = set()
    models: list[str] = []
    for item in value:
        model = str(item or "").strip()
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return tuple(models)


@dataclass(slots=True)
class ModelCatalogGroup:
    models: tuple[str, ...] = ()
    refreshed_at: str = ""
    source: str = ""
    provider_id: str = ""
    base_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "models": list(self.models),
            "refreshed_at": self.refreshed_at,
            "source": self.source,
            "provider_id": self.provider_id,
            "base_url": self.base_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ModelCatalogGroup":
        payload = data if isinstance(data, dict) else {}
        return cls(
            models=_coerce_models(payload.get("models")),
            refreshed_at=str(payload.get("refreshed_at") or "").strip(),
            source=str(payload.get("source") or "").strip(),
            provider_id=str(payload.get("provider_id") or "").strip(),
            base_url=str(payload.get("base_url") or "").strip(),
        )


def coerce_groups(value: Any) -> tuple[ModelCatalogGroup, ...]:
    if not isinstance(value, list):
        return ()
    groups: list[ModelCatalogGroup] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        group = ModelCatalogGroup.from_dict(item if isinstance(item, dict) else None)
        if not group_has_payload(group):
            continue
        key = group_key(group)
        if key in seen:
            continue
        seen.add(key)
        groups.append(group)
    return tuple(groups)


def group_key(group: ModelCatalogGroup) -> tuple[str, str]:
    return (
        str(group.provider_id or "").strip(),
        str(group.base_url or "").strip().rstrip("/"),
    )


def group_has_payload(group: ModelCatalogGroup) -> bool:
    return bool(group.models or group.refreshed_at or group.source or group.provider_id or group.base_url)


def merged_groups(current: ModelCatalogGroup, catalogs: tuple[ModelCatalogGroup, ...]) -> tuple[ModelCatalogGroup, ...]:
    merged: list[ModelCatalogGroup] = []
    seen: set[tuple[str, str]] = set()
    for group in (current, *catalogs):
        if not group_has_payload(group):
            continue
        key = group_key(group)
        if key in seen:
            continue
        seen.add(key)
        merged.append(group)
    return tuple(merged)


def group_matches_provider(group: ModelCatalogGroup, provider_settings: ProviderEndpointSettings) -> bool:
    group_provider_id = str(group.provider_id or "").strip()
    group_base_url = str(group.base_url or "").strip().rstrip("/")
    if not group_provider_id and not group_base_url:
        return (
            provider_settings.normalized_provider_id() == LEGACY_OPENAI_PROVIDER_ID
            and provider_settings.normalized_base_url() == LEGACY_OPENAI_BASE_URL
        )
    return (
        group_provider_id == provider_settings.normalized_provider_id()
        and group_base_url == provider_settings.normalized_base_url()
    )


__all__ = [
    "ModelCatalogGroup",
    "coerce_groups",
    "group_has_payload",
    "group_key",
    "group_matches_provider",
    "merged_groups",
]
