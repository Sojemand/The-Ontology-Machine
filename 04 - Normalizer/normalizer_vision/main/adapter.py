"""CLI adapter stage for logging and console output."""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ..normalizer import DocumentNormalizer
from ..paths import MODULE_ROOT


def setup_logging(*, resolve_log_dir: Callable[[], Path]) -> None:
    formatter_file = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    formatter_console = logging.Formatter("%(levelname)s: %(message)s")
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_path = resolve_log_dir()
    log_path.mkdir(parents=True, exist_ok=True)

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    file_handler = RotatingFileHandler(
        log_path / "normalizer_vision.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter_file)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter_console)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def load_normalizer(config_path: str | None, *, root: Path | None = None) -> DocumentNormalizer:
    cfg_path = Path(config_path) if config_path else None
    return DocumentNormalizer.from_project(root or MODULE_ROOT, config_path=cfg_path)


def print_error(message: str) -> None:
    print(f"Error: {message}")


def print_config_valid(profile_id: str) -> None:
    print(f"Config is valid. Profile: {profile_id}")


def print_config_invalid(message: str) -> None:
    print(f"Config invalid: {message}")


def print_taxonomy_analysis(report: dict[str, object], release_preview: dict[str, object]) -> None:
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSemantic Release Preview: {release_preview['release_id']} | {release_preview['fingerprint']}")
