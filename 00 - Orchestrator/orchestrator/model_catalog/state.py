"""Dataclass state for named model catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import ProviderEndpointSettings
from .groups import (
    ModelCatalogGroup,
    coerce_groups,
    group_has_payload,
    group_key,
    group_matches_provider,
    merged_groups,
)
from .targets import ModelCatalogTarget


@dataclass(slots=True)
class ModelCatalogState:
    schema_version: int = 2
    llm_shared: ModelCatalogGroup = field(default_factory=ModelCatalogGroup)
    optimizer_ocr: ModelCatalogGroup = field(default_factory=ModelCatalogGroup)
    embeddings: ModelCatalogGroup = field(default_factory=ModelCatalogGroup)
    llm_shared_catalogs: tuple[ModelCatalogGroup, ...] = ()
    optimizer_ocr_catalogs: tuple[ModelCatalogGroup, ...] = ()
    embeddings_catalogs: tuple[ModelCatalogGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "llm_shared": self.llm_shared.to_dict(),
            "optimizer_ocr": self.optimizer_ocr.to_dict(),
            "embeddings": self.embeddings.to_dict(),
            "llm_shared_catalogs": [group.to_dict() for group in self.groups_for("llm_shared")],
            "optimizer_ocr_catalogs": [group.to_dict() for group in self.groups_for("optimizer_ocr")],
            "embeddings_catalogs": [group.to_dict() for group in self.groups_for("embeddings")],
        }

    def group_for(
        self,
        target: ModelCatalogTarget,
        *,
        provider_settings: ProviderEndpointSettings | None = None,
    ) -> ModelCatalogGroup:
        current = self._current_group(target)
        if provider_settings is None:
            return current
        if group_matches_provider(current, provider_settings):
            return current
        for group in self.groups_for(target):
            if group_matches_provider(group, provider_settings):
                return group
        return ModelCatalogGroup()

    def groups_for(self, target: ModelCatalogTarget) -> tuple[ModelCatalogGroup, ...]:
        current = self._current_group(target)
        catalogs = self._catalogs(target)
        return merged_groups(current, catalogs)

    def replace_group(self, target: ModelCatalogTarget, group: ModelCatalogGroup) -> None:
        key = group_key(group)
        catalogs = [
            existing
            for existing in self.groups_for(target)
            if group_key(existing) != key
        ]
        if group_has_payload(group):
            catalogs.insert(0, group)
        if target == "llm_shared":
            self.llm_shared = group
            self.llm_shared_catalogs = tuple(catalogs)
        elif target == "optimizer_ocr":
            self.optimizer_ocr = group
            self.optimizer_ocr_catalogs = tuple(catalogs)
        else:
            self.embeddings = group
            self.embeddings_catalogs = tuple(catalogs)

    def _current_group(self, target: ModelCatalogTarget) -> ModelCatalogGroup:
        if target == "llm_shared":
            return self.llm_shared
        if target == "optimizer_ocr":
            return self.optimizer_ocr
        return self.embeddings

    def _catalogs(self, target: ModelCatalogTarget) -> tuple[ModelCatalogGroup, ...]:
        if target == "llm_shared":
            return self.llm_shared_catalogs
        if target == "optimizer_ocr":
            return self.optimizer_ocr_catalogs
        return self.embeddings_catalogs

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ModelCatalogState":
        payload = data if isinstance(data, dict) else {}
        schema_version = _schema_version(payload.get("schema_version", 1))
        llm_shared = ModelCatalogGroup.from_dict(payload.get("llm_shared"))
        optimizer_ocr = ModelCatalogGroup.from_dict(payload.get("optimizer_ocr"))
        embeddings = ModelCatalogGroup.from_dict(payload.get("embeddings"))
        llm_shared_catalogs = coerce_groups(payload.get("llm_shared_catalogs")) if schema_version >= 2 else merged_groups(llm_shared, ())
        optimizer_ocr_catalogs = coerce_groups(payload.get("optimizer_ocr_catalogs")) if schema_version >= 2 else merged_groups(optimizer_ocr, ())
        embeddings_catalogs = coerce_groups(payload.get("embeddings_catalogs")) if schema_version >= 2 else merged_groups(embeddings, ())
        if not group_has_payload(llm_shared) and llm_shared_catalogs:
            llm_shared = llm_shared_catalogs[0]
        if not group_has_payload(optimizer_ocr) and optimizer_ocr_catalogs:
            optimizer_ocr = optimizer_ocr_catalogs[0]
        if not group_has_payload(embeddings) and embeddings_catalogs:
            embeddings = embeddings_catalogs[0]
        return cls(
            schema_version=2,
            llm_shared=llm_shared,
            optimizer_ocr=optimizer_ocr,
            embeddings=embeddings,
            llm_shared_catalogs=merged_groups(llm_shared, llm_shared_catalogs),
            optimizer_ocr_catalogs=merged_groups(optimizer_ocr, optimizer_ocr_catalogs),
            embeddings_catalogs=merged_groups(embeddings, embeddings_catalogs),
        )


def _schema_version(value: Any) -> int:
    try:
        schema_version = int(value)
    except (TypeError, ValueError):
        schema_version = 1
    return max(schema_version, 1)


__all__ = ["ModelCatalogState"]
