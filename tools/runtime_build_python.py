from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from portable_runtime import pip_command, query_python_layout
from runtime_build_config import (
    ORCHESTRATOR_PYTHON_HOME_ENV,
    PIPELINE_ROOT,
    RUNTIME_PYTHON_BITS,
    RUNTIME_PYTHON_HOME_ENV,
    RUNTIME_PYTHON_VERSION,
)
from runtime_build_process import run


def ensure_host_pip(python_exe: Path, *, run_fn=run) -> None:
    try:
        run_fn(pip_command(python_exe, "--version"), cwd=PIPELINE_ROOT, capture_output=True)
    except subprocess.CalledProcessError:
        run_fn([str(python_exe), "-m", "ensurepip", "--upgrade"], cwd=PIPELINE_ROOT)


def python_bits(python_exe: Path, *, run_fn=run) -> int:
    completed = run_fn(
        [str(python_exe), "-c", "import struct; print(struct.calcsize('P') * 8)"],
        cwd=PIPELINE_ROOT,
        capture_output=True,
    )
    return int(completed.stdout.strip())


def launcher_python(*, run_fn=run, sys_platform: str | None = None) -> Path | None:
    if (sys_platform or sys.platform) != "win32":
        return None
    try:
        completed = run_fn(["py", "-3.11", "-c", "import sys; print(sys.executable)"], cwd=PIPELINE_ROOT, capture_output=True)
    except Exception:
        return None
    value = completed.stdout.strip()
    return Path(value).resolve() if value else None


def runtime_python_candidates(requested_python: str | None, *, run_fn=run, sys_platform: str | None = None) -> list[Path]:
    candidates: list[Path] = [Path(requested_python)] if requested_python else []
    for env_name in (RUNTIME_PYTHON_HOME_ENV, ORCHESTRATOR_PYTHON_HOME_ENV):
        if override := os.environ.get(env_name, "").strip():
            candidates.append(Path(override))
    for root in (os.environ.get("LocalAppData", "").strip(), os.environ.get("ProgramFiles", "").strip()):
        if root:
            base = Path(root)
            candidates.append(base / "Programs" / "Python" / "Python311")
            candidates.append(base / "Python311")
    candidates.extend([Path(sys.base_prefix), Path(sys.executable)])
    if launcher := launcher_python(run_fn=run_fn, sys_platform=sys_platform):
        candidates.append(launcher)
    return _dedupe_python_candidates(candidates)


def resolve_runtime_base_python(
    requested_python: str | None,
    *,
    purpose: str = "Runtime",
    sys_platform: str | None = None,
    candidates_fn: Callable[[str | None], list[Path]] | None = None,
    query_layout_fn=query_python_layout,
    python_bits_fn: Callable[[Path], int] | None = None,
) -> Path:
    if (sys_platform or sys.platform) != "win32":
        raise RuntimeError(f"Der {purpose}-Build wird nur unter Windows unterstuetzt.")
    bits_fn = python_bits_fn or (lambda candidate: python_bits(candidate))
    if requested_python:
        return _resolve_explicit_python(requested_python, purpose=purpose, query_layout_fn=query_layout_fn, bits_fn=bits_fn)
    for candidate in (candidates_fn or runtime_python_candidates)(None):
        if not candidate.exists():
            continue
        try:
            layout = query_layout_fn(candidate)
            bits = bits_fn(layout.python_exe)
        except Exception:
            continue
        if layout.platform == "win32" and layout.version_info[:2] == RUNTIME_PYTHON_VERSION and bits == RUNTIME_PYTHON_BITS:
            return layout.python_exe
    raise FileNotFoundError(
        "Keine lokale CPython-3.11-x64-Installation gefunden. "
        f"Setze optional {RUNTIME_PYTHON_HOME_ENV} auf den Python311-Ordner."
    )


def resolve_orchestrator_base_python(requested_python: str | None, **kwargs) -> Path:
    return resolve_runtime_base_python(requested_python, purpose="Orchestrator-Runtime", **kwargs)


def _resolve_explicit_python(requested_python: str, *, purpose: str, query_layout_fn, bits_fn) -> Path:
    del purpose
    requested_candidate = Path(requested_python)
    if requested_candidate.is_dir():
        requested_candidate = requested_candidate / "python.exe"
    if not requested_candidate.exists():
        raise FileNotFoundError(f"Angegebene Python-3.11-x64-Executable wurde nicht gefunden: {requested_candidate}")
    layout = query_layout_fn(requested_candidate)
    bits = bits_fn(layout.python_exe)
    if layout.platform == "win32" and layout.version_info[:2] == RUNTIME_PYTHON_VERSION and bits == RUNTIME_PYTHON_BITS:
        return layout.python_exe
    raise RuntimeError(
        "Angegebene Python-Executable ist nicht CPython 3.11 x64: "
        f"{layout.python_exe} ({layout.version_text}, {bits}-bit)"
    )


def _dedupe_python_candidates(candidates: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.is_dir():
            candidate = candidate / "python.exe"
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            resolved.append(candidate)
    return resolved
