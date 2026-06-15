"""Headless runtime helpers shared by the orchestrator contract."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .models.config import LOCAL_ENV_BLOCKED_KEYS, load_dotenv_file
from .runtime_paths import ensure_logs_dir, resolve_runtime_paths

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv() -> None:
    load_dotenv_file(resolve_runtime_paths().env_file, blocked_keys=LOCAL_ENV_BLOCKED_KEYS)


def setup_logging() -> None:
    runtime_paths = resolve_runtime_paths()
    ensure_logs_dir(runtime_paths)
    root = logging.getLogger()
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(getattr(logging, level, logging.INFO))
    if not _has_file_handler(root, runtime_paths.log_file):
        handler = RotatingFileHandler(
            runtime_paths.log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    if not _has_console_handler(root):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root.addHandler(handler)


def _has_file_handler(root: logging.Logger, log_file: Path) -> bool:
    target = log_file.resolve(strict=False)
    for handler in root.handlers:
        base_name = getattr(handler, "baseFilename", "")
        if base_name and Path(base_name).resolve(strict=False) == target:
            return True
    return False


def _has_console_handler(root: logging.Logger) -> bool:
    return any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in root.handlers
    )
