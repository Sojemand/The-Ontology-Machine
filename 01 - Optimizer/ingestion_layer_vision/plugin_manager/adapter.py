"""Boundary helpers for the static Vision extractor registry."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from . import validation
from .policy import _INLINE_EXTRACTORS

logger = logging.getLogger(__name__)


def plugin_dir(registry, name: str) -> Path:
    if name in _INLINE_EXTRACTORS:
        return registry._bundled_dir / name
    return registry._dir / name


def load_manifest(plugin_dir: Path, fallback_name: str):
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("plugin.json load failed for %s: %s", plugin_dir.name, exc)
        return None
    if not isinstance(data, dict):
        logger.warning("plugin.json load failed for %s: root payload must be an object", plugin_dir.name)
        return None
    return validation.build_manifest(data, fallback_name)
