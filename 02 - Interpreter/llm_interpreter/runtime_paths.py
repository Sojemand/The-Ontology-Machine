"""Runtime path policy for mutable interpreter artefacts."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

RUNTIME_HOME_ENV = "INTERPRETER_HOME"
_APP_VENDOR = "Enterprise Stack"
_APP_NAME = "Interpreter"
MODULE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RuntimePaths:
    home: Path
    config_dir: Path
    env_file: Path
    state_dir: Path
    logs_dir: Path
    log_file: Path
    output_dir: Path


def resolve_runtime_paths(environ: Mapping[str, str] | None = None) -> RuntimePaths:
    home = _resolve_runtime_home(environ)
    config_dir = home / "config"
    state_dir = home / "state"
    logs_dir = home / "logs"
    output_dir = home / "output"
    return RuntimePaths(
        home=home,
        config_dir=config_dir,
        env_file=config_dir / ".env",
        state_dir=state_dir,
        logs_dir=logs_dir,
        log_file=logs_dir / "llm_interpreter.log",
        output_dir=output_dir,
    )


def ensure_config_dir(paths: RuntimePaths) -> Path:
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    return paths.config_dir


def ensure_state_dir(paths: RuntimePaths) -> Path:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    return paths.state_dir


def ensure_logs_dir(paths: RuntimePaths) -> Path:
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    return paths.logs_dir


def ensure_output_dir(paths: RuntimePaths) -> Path:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    return paths.output_dir


def _resolve_runtime_home(environ: Mapping[str, str] | None) -> Path:
    env = os.environ if environ is None else environ
    override = str(env.get(RUNTIME_HOME_ENV, "")).strip()
    if override:
        return Path(override).expanduser().resolve(strict=False)
    local_app_data = _local_appdata(env)
    if local_app_data:
        return (Path(local_app_data) / _APP_VENDOR / _APP_NAME).resolve(strict=False)
    return (MODULE_ROOT / ".appdata").resolve(strict=False)


def _local_appdata(environ: Mapping[str, str]) -> str:
    for key in ("LOCALAPPDATA", "LocalAppData"):
        value = str(environ.get(key, "")).strip()
        if value:
            return value
    return ""
