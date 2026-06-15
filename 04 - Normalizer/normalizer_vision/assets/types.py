"""Named carriers for source-backed asset discovery."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..runtime_semantic_assets.types import (
    RuntimeProjectionCatalog as ProjectionCatalog,
    RuntimeProjectionCatalogEntry as ProjectionCatalogEntry,
)


@dataclass(frozen=True, slots=True)
class LocalProfileSpec:
    projection_id: str
    label: str
    source_path: Path
