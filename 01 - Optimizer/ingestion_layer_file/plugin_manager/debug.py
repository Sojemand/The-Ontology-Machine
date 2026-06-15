"""Debug helpers for plugin manager stage logs and shared env defaults."""
from __future__ import annotations

import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


def subprocess_env_defaults() -> dict[str, str]:
    package = sys.modules[__package__]
    return dict(getattr(package, "_SUBPROCESS_ENV"))


def log_manifest_load_failed(plugin_dir: Path, exc: Exception) -> None:
    logger.warning("plugin_manager.adapter.manifest_load_failed %s: %s", plugin_dir.name, exc)


def log_inline_extract_failed(name: str, file_path: Path, exc: Exception) -> None:
    logger.warning("plugin_manager.workflow.inline_extract_failed %s for %s: %s", name, file_path, exc)
