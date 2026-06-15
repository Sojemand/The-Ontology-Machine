"""Compiled taxonomy asset carriers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CompiledTaxonomyAssets:
    master: dict[str, Any]
    projections: dict[str, dict[str, Any]]
    release: dict[str, Any]
