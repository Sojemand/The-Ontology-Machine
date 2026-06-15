"""Config loading for the models surface."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .runtime_types import IngestionConfig
from .validation import CONFIG_MINIMUMS, VALID_PROCESSING_ORDERS, validate_config_payload

try:
    import yaml
except ImportError:  # pragma: no cover - fallback for minimal environments
    yaml = None

logger = logging.getLogger(__name__)


def require_yaml_module():
    if yaml is None:
        raise ModuleNotFoundError("yaml ist fuer die Settings-Surface erforderlich.")
    return yaml


def read_config_payload(config_path: Path) -> dict[str, Any]:
    yaml_module = require_yaml_module()
    if not Path(config_path).exists():
        return validate_config_payload({})
    data = yaml_module.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    return validate_config_payload(data)


def load_config(config_path: Path) -> IngestionConfig:
    try:
        raw_text = Path(config_path).read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Config load failed (%s), using defaults", exc)
        return IngestionConfig()
    if yaml is not None:
        try:
            data = yaml.safe_load(raw_text) or {}
            if not isinstance(data, dict):
                raise ValueError("invalid yaml payload")
            return parse_ingestion_config(data)
        except Exception as exc:
            logger.warning("Config parse failed (%s), trying line-based fallback", exc)
    parsed: dict[str, Any] = {}
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        parsed[key.strip()] = value.strip().strip("'\"")
    return parse_ingestion_config(parsed)


def parse_ingestion_config(data: dict[str, Any]) -> IngestionConfig:
    if not isinstance(data, dict):
        logger.warning("Config payload ist kein Mapping, verwende Defaults")
        return IngestionConfig()
    defaults = IngestionConfig()
    return IngestionConfig(
        max_file_size_mb=_coerce_config_int(data.get("max_file_size_mb"), defaults.max_file_size_mb, field_name="max_file_size_mb"),
        max_blocks_per_file=_coerce_config_int(data.get("max_blocks_per_file"), defaults.max_blocks_per_file, field_name="max_blocks_per_file"),
        max_cell_text_length=_coerce_config_int(data.get("max_cell_text_length"), defaults.max_cell_text_length, field_name="max_cell_text_length"),
        processing_order=_normalize_processing_order(data.get("processing_order"), defaults.processing_order),
        plugin_timeout_seconds=_coerce_config_int(data.get("plugin_timeout_seconds"), defaults.plugin_timeout_seconds, field_name="plugin_timeout_seconds"),
        parallel_workers=_coerce_config_int(data.get("parallel_workers"), defaults.parallel_workers, field_name="parallel_workers"),
        render_dpi=_coerce_config_int(data.get("render_dpi"), defaults.render_dpi, field_name="render_dpi"),
        render_width_px=_coerce_config_int(data.get("render_width_px"), defaults.render_width_px, field_name="render_width_px"),
        render_height_px=_coerce_config_int(data.get("render_height_px"), defaults.render_height_px, field_name="render_height_px"),
        page_margin_pt=_coerce_config_int(data.get("page_margin_pt"), defaults.page_margin_pt, field_name="page_margin_pt"),
        default_font_size_pt=_coerce_config_int(data.get("default_font_size_pt"), defaults.default_font_size_pt, field_name="default_font_size_pt"),
        code_font_size_pt=_coerce_config_int(data.get("code_font_size_pt"), defaults.code_font_size_pt, field_name="code_font_size_pt"),
        heading_font_size_pt=_coerce_config_int(data.get("heading_font_size_pt"), defaults.heading_font_size_pt, field_name="heading_font_size_pt"),
    )
def _coerce_config_int(value: Any, default: int, *, field_name: str) -> int:
    if value is None:
        return default
    candidate: int | None = None
    if isinstance(value, int) and not isinstance(value, bool):
        candidate = value
    elif isinstance(value, float) and value.is_integer():
        candidate = int(value)
    elif isinstance(value, str):
        try:
            candidate = int(value.strip())
        except ValueError:
            candidate = None
    minimum = CONFIG_MINIMUMS[field_name]
    if candidate is None or candidate < minimum:
        logger.warning("Ungueltiger Config-Wert fuer %s: %r, verwende Default %r", field_name, value, default)
        return default
    return candidate


def _normalize_processing_order(value: Any, default: str) -> str:
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in VALID_PROCESSING_ORDERS:
            return candidate
    if value is not None:
        logger.warning("Ungueltiger Config-Wert fuer processing_order: %r, verwende Default %r", value, default)
    return default
