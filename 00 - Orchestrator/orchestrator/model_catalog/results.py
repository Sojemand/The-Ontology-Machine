"""Refresh result types for model catalogs."""

from __future__ import annotations

from dataclasses import dataclass

from .state import ModelCatalogState
from .targets import ModelCatalogTarget


@dataclass(frozen=True, slots=True)
class GroupRefreshResult:
    target: ModelCatalogTarget
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class CatalogRefreshResult:
    state: ModelCatalogState
    group_results: dict[ModelCatalogTarget, GroupRefreshResult]


__all__ = ["CatalogRefreshResult", "GroupRefreshResult"]
