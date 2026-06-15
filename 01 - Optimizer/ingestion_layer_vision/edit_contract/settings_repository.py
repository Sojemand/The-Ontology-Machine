"""Settings-only repository helpers that require YAML support."""
from __future__ import annotations

from ..models.repository import atomic_text_write
from ingestion_layer_file.models.config import read_config_payload
from ingestion_layer_file.models.validation import config_to_dict, validate_config_payload
import yaml


def read_settings(layout) -> dict:
    return read_config_payload(layout.default_config_path)


def write_settings(layout, payload: dict) -> dict:
    normalized = validate_config_payload(payload)
    yaml_text = yaml.safe_dump(config_to_dict(normalized), sort_keys=False)
    atomic_text_write(layout.default_config_path, yaml_text)
    return normalized
