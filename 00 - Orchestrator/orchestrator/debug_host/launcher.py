"""Process launcher wrapper for generic debug-host module steps."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..bootstrap import ModuleRuntimeSpec
from ..integrations import adapter
from .types import DebugProcessHandle

SESSION_HOME_BOOTSTRAP_TIMEOUT_SECONDS = 30


def launch_process(
    spec: ModuleRuntimeSpec,
    payload: dict[str, Any],
    *,
    request_path: Path,
    response_path: Path,
    env_overlay: dict[str, str] | None = None,
    bootstrap_home: Path | None = None,
) -> DebugProcessHandle:
    prepare_session_home(spec, env_overlay=env_overlay, bootstrap_home=bootstrap_home)
    process = adapter.launch_contract_process(
        spec,
        payload,
        request_path=request_path,
        response_path=response_path,
        env_overlay=env_overlay,
    )
    return DebugProcessHandle(process=process, request_path=request_path, response_path=response_path)


def prepare_session_home(
    spec: ModuleRuntimeSpec,
    *,
    env_overlay: dict[str, str] | None,
    bootstrap_home: Path | None,
) -> None:
    if bootstrap_home is None:
        return
    package_name = str(spec.contract_module or "").split(".", 1)[0].strip()
    if not package_name:
        return
    bootstrap_module = f"{package_name}.config_bootstrap"
    bootstrap_script = spec.module_root.joinpath(*package_name.split("."), "config_bootstrap.py")
    if not bootstrap_script.is_file():
        return
    try:
        completed = subprocess.run(
            [
                str(spec.python_executable),
                "-m",
                bootstrap_module,
                "--app-home",
                str(bootstrap_home),
            ],
            cwd=spec.module_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SESSION_HOME_BOOTSTRAP_TIMEOUT_SECONDS,
            env=adapter.runtime_subprocess_env(spec, env_overlay=env_overlay),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{spec.display_name} could not bootstrap session_home within "
            f"{SESSION_HOME_BOOTSTRAP_TIMEOUT_SECONDS}s"
        ) from exc
    if completed.returncode == 0:
        return
    detail = (completed.stderr or completed.stdout or "").strip()
    suffix = f": {detail}" if detail else ""
    raise RuntimeError(f"{spec.display_name} could not bootstrap session_home{suffix}")
