"""Target identifiers for orchestrator model catalogs."""

from __future__ import annotations

from typing import Literal

ModelCatalogTarget = Literal["llm_shared", "optimizer_ocr", "embeddings"]

LEGACY_OPENAI_PROVIDER_ID = "openai"
LEGACY_OPENAI_BASE_URL = "https://api.openai.com/v1"


__all__ = [
    "LEGACY_OPENAI_BASE_URL",
    "LEGACY_OPENAI_PROVIDER_ID",
    "ModelCatalogTarget",
]
