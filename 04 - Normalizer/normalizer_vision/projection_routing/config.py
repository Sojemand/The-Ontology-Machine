"""Config-backed settings for projection selection."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..projection_routing_settings import default_routing_settings, validate_routing_settings


def load_routing_settings(project_root: Path) -> dict[str, int | float]:
    config_path = Path(project_root) / "config" / "config.yaml"
    if not config_path.exists():
        return default_routing_settings()
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ValueError(f"projection_routing konnte nicht geladen werden: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("config.yaml muss ein Objekt enthalten.")
    return validate_routing_settings(payload.get("projection_routing", {}))


__all__ = ["default_routing_settings", "load_routing_settings", "validate_routing_settings"]
