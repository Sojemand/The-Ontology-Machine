"""Low-level subprocess adapter for owner-provided contracts."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path

from .. import policy, validation

_ISOLATED_PYTHON_ENV_VARS = (
    "PYTHONHOME",
    "PYTHONPATH",
    "VIRTUAL_ENV",
    "__PYVENV_LAUNCHER__",
    "TCL_LIBRARY",
    "TK_LIBRARY",
)
_CONTRACT_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_CONTRACT_TEMP_CLEANUP_INTERVAL_SECONDS = 60
_LAST_CONTRACT_TEMP_CLEANUP: dict[tuple[str, int], float] = {}


def invoke_owner_contract(*, module_root: Path, contract_path: str, state_root: Path, payload: dict, timeout_seconds: int | None = None) -> dict:
    contract_module = _contract_module(module_root, Path(contract_path))
    return invoke_module_contract(
        module_root=module_root,
        contract_module=contract_module,
        state_root=state_root,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def invoke_module_contract(*, module_root: Path, contract_module: str, state_root: Path, payload: dict, timeout_seconds: int | None = None) -> dict:
    state_root.mkdir(parents=True, exist_ok=True)
    _cleanup_stale_contract_tempdirs_if_due(state_root)
    _require_contract_module(contract_module)
    python_exe = _contract_python(module_root)
    timeout = _contract_timeout_seconds(timeout_seconds)
    with tempfile.TemporaryDirectory(prefix=policy.CONTRACT_TEMP_PREFIX, dir=str(state_root)) as temp_dir:
        request_path = Path(temp_dir) / "request.json"
        response_path = Path(temp_dir) / "response.json"
        request_path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            completed = subprocess.run(
                [str(python_exe), "-m", contract_module, "--request", str(request_path), "--response", str(response_path)],
                cwd=module_root,
                capture_output=True,
                text=True,
                check=False,
                env=_contract_env(),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Owner contract timed out after {timeout} seconds: {contract_module}") from exc
        if completed.returncode != 0:
            detail = completed.stderr or completed.stdout or f"Contract-Exitcode {completed.returncode}"
            raise RuntimeError(detail.strip())
        if not response_path.exists():
            raise RuntimeError(f"Owner contract did not write a response: {contract_module}")
        response = json.loads(response_path.read_text(encoding="utf-8"))
        return validation.require_json_object(response, label=f"{contract_module} response")


def cleanup_stale_contract_tempdirs(state_root: Path, *, max_age_seconds: int = policy.CONTRACT_TEMP_MAX_AGE_SECONDS) -> None:
    now = time.time()
    for path in state_root.glob(f"{policy.CONTRACT_TEMP_PREFIX}*"):
        if not path.is_dir():
            continue
        try:
            validation.ensure_state_child(state_root, path)
            if now - path.stat().st_mtime < max_age_seconds:
                continue
            shutil.rmtree(path)
        except Exception:
            continue


def _cleanup_stale_contract_tempdirs_if_due(state_root: Path, *, max_age_seconds: int = policy.CONTRACT_TEMP_MAX_AGE_SECONDS) -> None:
    now = time.time()
    key = (str(state_root.resolve()), int(max_age_seconds))
    last = _LAST_CONTRACT_TEMP_CLEANUP.get(key, 0.0)
    if now - last < _CONTRACT_TEMP_CLEANUP_INTERVAL_SECONDS:
        return
    _LAST_CONTRACT_TEMP_CLEANUP[key] = now
    cleanup_stale_contract_tempdirs(state_root, max_age_seconds=max_age_seconds)


def _contract_module(module_root: Path, contract_path: Path) -> str:
    anchored = contract_path if contract_path.is_absolute() else module_root / contract_path
    return _contract_module_cached(str(module_root.resolve()), str(anchored.resolve()))


@lru_cache(maxsize=256)
def _contract_module_cached(module_root: str, contract_path: str) -> str:
    return ".".join(Path(contract_path).relative_to(Path(module_root)).parts)


def _require_contract_module(contract_module: str) -> None:
    if not _CONTRACT_MODULE_RE.match(str(contract_module or "").strip()):
        raise ValueError(f"Invalid contract module: {contract_module or '<empty>'}")


def _contract_python(module_root: Path) -> Path:
    return Path(_contract_python_cached(str(module_root.resolve())))


@lru_cache(maxsize=64)
def _contract_python_cached(module_root: str) -> str:
    module_root_path = Path(module_root)
    runtime_root = module_root_path / "runtime" / "python"
    for candidate in ("python.exe", "Scripts/python.exe", "bin/python"):
        python_exe = runtime_root / candidate
        if python_exe.is_file():
            return str(python_exe)
    raise FileNotFoundError(f"No module runtime found: {runtime_root}")


def _contract_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _ISOLATED_PYTHON_ENV_VARS:
        env.pop(key, None)
    env["PYTHONNOUSERSITE"] = "1"
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def _contract_timeout_seconds(timeout_seconds: int | None) -> int:
    if timeout_seconds is not None:
        timeout = int(timeout_seconds)
        if timeout < 1:
            raise ValueError("Owner contract timeout must be at least 1 second.")
        return timeout
    raw = os.environ.get("EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS", "")
    if raw.strip():
        try:
            timeout = int(raw)
        except ValueError:
            raise ValueError("EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS must be an integer number of seconds.")
        if timeout < 1:
            raise ValueError("EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS must be at least 1 second.")
        return timeout
    return policy.OWNER_CONTRACT_TIMEOUT_SECONDS
