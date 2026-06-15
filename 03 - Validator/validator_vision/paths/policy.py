"""Path policy stage for Validator Vision runtime locations."""
from __future__ import annotations

import os
from pathlib import Path

from .types import PathLayout

_ENV_HOME = "VALIDATOR_VISION_HOME"
_APP_VENDOR = "Enterprise Stack"
_APP_NAME = "Validator Vision"
_CONFIG_DIR = "config"
_STATE_DIR = "state"
_OUTPUT_DIR = "output"
_LOG_DIR = "logs"

MODULE_ROOT = Path(__file__).resolve().parent.parent.parent


def module_root() -> Path:
    return MODULE_ROOT


def bundled_config_path(root: Path | None = None) -> Path:
    return Path(root or MODULE_ROOT) / _CONFIG_DIR / "config.json"


def app_home(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    return _env_home() or _fallback_home()


def config_dir(root: Path | None = None) -> Path:
    return _build_layout(root).config_dir


def state_dir(root: Path | None = None) -> Path:
    return _build_layout(root).state_dir


def default_output_dir(root: Path | None = None) -> Path:
    return _build_layout(root).output_dir


def log_dir(root: Path | None = None) -> Path:
    return _build_layout(root).log_dir


def default_config_path(root: Path | None = None) -> Path:
    return _build_layout(root).default_config_path


def _env_home() -> Path | None:
    override = os.getenv(_ENV_HOME, "").strip()
    if override:
        return Path(override).expanduser()
    local_appdata = os.getenv("LOCALAPPDATA", "").strip()
    if local_appdata:
        return Path(local_appdata) / _APP_VENDOR / _APP_NAME
    return None


def _fallback_home() -> Path:
    return MODULE_ROOT / ".appdata"


def _build_layout(root: Path | None = None) -> PathLayout:
    home = app_home(root)
    return PathLayout(
        module_root=MODULE_ROOT,
        app_home=home,
        config_dir=home / _CONFIG_DIR,
        state_dir=home / _STATE_DIR,
        output_dir=home / _OUTPUT_DIR,
        log_dir=home / _LOG_DIR,
        bundled_config_path=bundled_config_path(),
        default_config_path=home / _CONFIG_DIR / "config.json",
    )
