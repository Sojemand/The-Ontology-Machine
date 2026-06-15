"""Repository stage for persisted orchestrator model catalog state."""

from __future__ import annotations

import logging
from pathlib import Path

from ..state.adapter import atomic_json_write, load_json_object
from .types import ModelCatalogState

logger = logging.getLogger(__name__)


def model_catalog_state_path(state_dir: Path) -> Path:
    return Path(state_dir) / "model_catalog_state.json"


def load_model_catalog_state(state_dir: Path) -> ModelCatalogState:
    path = model_catalog_state_path(state_dir)
    payload = load_json_object(
        path,
        read_error="Could not load model catalog state: %s",
        invalid_format="Model-Catalog-State hat ungueltiges Format: %s",
    )
    if payload is None:
        return ModelCatalogState()
    try:
        return ModelCatalogState.from_dict(payload)
    except Exception:
        logger.warning("Model catalog state could not be deserialized: %s", path, exc_info=True)
        return ModelCatalogState()


def save_model_catalog_state(state_dir: Path, state: ModelCatalogState) -> None:
    atomic_json_write(model_catalog_state_path(state_dir), state.to_dict())
