"""Config loading for the models surface."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .runtime_types import IngestionConfig
from .validation import validate_config_payload


def read_config_payload(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return validate_config_payload({})
    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return validate_config_payload(data)


def load_config(config_path: Path) -> IngestionConfig:
    return IngestionConfig(**read_config_payload(config_path))
