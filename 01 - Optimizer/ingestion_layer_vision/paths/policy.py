"""Path policy stage for Optimizer runtime locations."""
from __future__ import annotations

import os
from pathlib import Path

from .types import PathLayout

_ENV_HOME = "OPTIMIZER_HOME"
_APP_VENDOR = "Enterprise Stack"
_APP_NAME = "Optimizer"
_CONFIG_DIR = "config"
_STATE_DIR = "state"
_OUTPUT_DIR = "output"
_LOG_DIR = "logs"
_PLUGINS_DIR = "plugins"
_RUNTIME_DIR = "runtime"

MODULE_ROOT = Path(__file__).resolve().parents[2]


def module_root(root: Path | None = None) -> Path:
    return Path(root or MODULE_ROOT)


def app_home(root: Path | None = None, *, module_root_path: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    return _env_home() or _fallback_home(module_root_path)


def config_dir(module_root_path: Path | None = None, app_home_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, app_home_path).config_dir


def state_dir(module_root_path: Path | None = None, app_home_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, app_home_path).state_dir


def output_dir(module_root_path: Path | None = None, app_home_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, app_home_path).output_dir


def log_dir(module_root_path: Path | None = None, app_home_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, app_home_path).log_dir


def plugins_dir(module_root_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, None).plugins_dir


def runtime_dir(module_root_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, None).runtime_dir


def bundled_config_dir(module_root_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, None).bundled_config_dir


def default_config_path(module_root_path: Path | None = None, app_home_path: Path | None = None) -> Path:
    return _build_layout(module_root_path, app_home_path).default_config_path


def _env_home() -> Path | None:
    override = os.getenv(_ENV_HOME, "").strip()
    if override:
        return Path(override).expanduser()
    local_appdata = os.getenv("LOCALAPPDATA", "").strip()
    if local_appdata:
        return Path(local_appdata) / _APP_VENDOR / _APP_NAME
    return None


def _fallback_home(module_root_path: Path | None = None) -> Path:
    return module_root(module_root_path) / ".appdata"


def _build_layout(module_root_path: Path | None = None, app_home_path: Path | None = None) -> PathLayout:
    resolved_module_root = module_root(module_root_path)
    resolved_app_home = app_home(app_home_path, module_root_path=resolved_module_root)
    return PathLayout(
        module_root=resolved_module_root,
        app_home=resolved_app_home,
        config_dir=resolved_app_home / _CONFIG_DIR,
        state_dir=resolved_app_home / _STATE_DIR,
        output_dir=resolved_app_home / _OUTPUT_DIR,
        log_dir=resolved_app_home / _LOG_DIR,
        plugins_dir=resolved_module_root / _PLUGINS_DIR,
        runtime_dir=resolved_module_root / _RUNTIME_DIR,
        bundled_config_dir=resolved_module_root / _CONFIG_DIR,
        default_config_path=resolved_app_home / _CONFIG_DIR / "config.yaml",
    )

