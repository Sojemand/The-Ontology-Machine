"""Adapter boundary for subprocess-based sibling-module contracts."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..bootstrap import ModuleRuntimeSpec
from ..state import atomic_json_write
from .contract_parsing import (
    contract_failure_text,
    parse_classification_result,
    parse_corpus_load_result,
    parse_dependency_statuses,
    parse_embedding_result,
    parse_extraction_result,
    parse_health_status,
    parse_interpretation_result,
    parse_normalization_result,
    parse_release_activation_result,
    parse_validation_result,
    response_error,
)
from .types import ModuleContractError
from .validation import ensure_contract_runtime_ready, load_contract_response

_SUBPROCESS_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}


def runtime_subprocess_env(spec: ModuleRuntimeSpec, *, env_overlay: dict[str, str] | None = None) -> dict[str, str]:
    env = {**_SUBPROCESS_ENV, "PYTHONHOME": str(spec.runtime_dir), "PYTHONPATH": "", "PYTHONNOUSERSITE": "1"}
    tcl_dir = spec.runtime_dir / "tcl"
    if (tcl_dir / "tcl8.6").exists():
        env["TCL_LIBRARY"] = (tcl_dir / "tcl8.6").as_posix()
    if (tcl_dir / "tk8.6").exists():
        env["TK_LIBRARY"] = (tcl_dir / "tk8.6").as_posix()
    for key, value in (env_overlay or {}).items():
        env[str(key)] = str(value)
    return env


def invoke_contract(
    spec: ModuleRuntimeSpec,
    payload: dict[str, Any],
    *,
    timeout: int,
    env_overlay: dict[str, str] | None = None,
) -> dict[str, Any]:
    ensure_contract_runtime_ready(
        display_name=spec.display_name,
        python_executable=spec.python_executable,
        manifest_path=spec.manifest_path,
    )
    with tempfile.TemporaryDirectory(prefix=f"vp-{spec.key}-contract-") as temp_dir:
        temp_root = Path(temp_dir)
        request_path = temp_root / "request.json"
        response_path = temp_root / "response.json"
        _write_contract_request(request_path, payload)
        try:
            completed = subprocess.run(
                _contract_command(spec, request_path=request_path, response_path=response_path),
                cwd=spec.module_root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=runtime_subprocess_env(spec, env_overlay=env_overlay),
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Bundled runtime is missing or cannot be started for {spec.display_name}: {spec.python_executable}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ModuleContractError(f"{spec.display_name} exceeded the time limit ({timeout}s).") from exc

        data = load_contract_response(response_path)
        if completed.returncode != 0:
            raise ModuleContractError(contract_failure_text(spec.display_name, completed, data))
        return data


def launch_contract_process(
    spec: ModuleRuntimeSpec,
    payload: dict[str, Any],
    *,
    request_path: Path,
    response_path: Path,
    env_overlay: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    ensure_contract_runtime_ready(
        display_name=spec.display_name,
        python_executable=spec.python_executable,
        manifest_path=spec.manifest_path,
    )
    _write_contract_request(request_path, payload)
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.unlink(missing_ok=True)
    try:
        return subprocess.Popen(
            _contract_command(spec, request_path=request_path, response_path=response_path),
            cwd=spec.module_root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=runtime_subprocess_env(spec, env_overlay=env_overlay),
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Bundled runtime is missing or cannot be started for {spec.display_name}: {spec.python_executable}"
        ) from exc


def _write_contract_request(path: Path, payload: dict[str, Any]) -> None:
    atomic_json_write(path, payload, indent=None)


def _contract_command(
    spec: ModuleRuntimeSpec,
    *,
    request_path: Path,
    response_path: Path,
) -> list[str]:
    return [
        str(spec.python_executable),
        "-m",
        spec.contract_module,
        "--request",
        str(request_path),
        "--response",
        str(response_path),
    ]
