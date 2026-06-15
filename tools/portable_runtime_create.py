from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from portable_runtime_layout import query_python_layout, runtime_python, site_packages_dir
from portable_runtime_validation import ensure_portable_runtime, is_portable_runtime


def detect_base_python(
    *,
    requested: str | Path | None = None,
    runtime_dir: str | Path | None = None,
    install_state_path: str | Path | None = None,
) -> Path:
    candidates: list[Path] = []
    if requested:
        candidates.append(Path(requested))
    candidates.extend(_install_state_candidates(install_state_path))
    candidates.extend(_runtime_candidates(runtime_dir))
    candidates.append(Path(sys.executable))
    for candidate in candidates:
        resolved = _resolve_python_candidate(candidate)
        if resolved is not None:
            return resolved
    raise FileNotFoundError("No usable base Python executable found")


def create_portable_runtime(
    runtime_dir: str | Path,
    *,
    base_python: str | Path,
    clean: bool = True,
    with_pip: bool = True,
):
    layout = query_python_layout(base_python)
    runtime_root = Path(runtime_dir)
    if clean and runtime_root.exists():
        shutil.rmtree(runtime_root, ignore_errors=False)
    runtime_root.mkdir(parents=True, exist_ok=True)
    for source in _root_files_to_copy(layout.home):
        shutil.copy2(source, runtime_root / source.name)
    for directory in _directories_to_copy(layout.home):
        destination = runtime_root / directory.name
        if destination.exists() and clean:
            shutil.rmtree(destination, ignore_errors=False)
        shutil.copytree(directory, destination, dirs_exist_ok=not clean, ignore=_copy_ignore)
    (runtime_root / "pyvenv.cfg").unlink(missing_ok=True)
    site_packages_dir(runtime_root, version_info=layout.version_info, platform=layout.platform).mkdir(parents=True, exist_ok=True)
    if with_pip:
        ensure_pip(runtime_root)
    ensure_portable_runtime(runtime_root)
    return layout


def ensure_pip(runtime_dir: str | Path) -> Path:
    root = Path(runtime_dir)
    python_exe = runtime_python(root)
    command = [str(python_exe), "-m", "ensurepip", "--upgrade", "--default-pip"]
    attempts = 6 if sys.platform == "win32" else 1
    for attempt in range(attempts):
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
            break
        except FileNotFoundError:
            if attempt + 1 >= attempts:
                raise
            time.sleep(0.5)
    return python_exe


def pip_command(python_exe: str | Path, *args: str) -> list[str]:
    return [str(python_exe), "-m", "pip", "--disable-pip-version-check", *args]


def _install_state_candidates(install_state_path: str | Path | None) -> list[Path]:
    if not install_state_path:
        return []
    state_path = Path(install_state_path)
    if not state_path.exists():
        return []
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    base_python = str(payload.get("base_python", "")).strip()
    return [Path(base_python)] if base_python else []


def _runtime_candidates(runtime_dir: str | Path | None) -> list[Path]:
    if not runtime_dir:
        return []
    root = Path(runtime_dir)
    candidates: list[Path] = []
    bundled_python = runtime_python(root)
    if bundled_python.exists() and is_portable_runtime(root):
        candidates.append(bundled_python)
    cfg_path = root / "pyvenv.cfg"
    if cfg_path.exists():
        candidates.extend(_pyvenv_home_candidates(cfg_path))
    return candidates


def _pyvenv_home_candidates(cfg_path: Path) -> list[Path]:
    try:
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            if not line.lower().startswith("home"):
                continue
            _key, value = line.split("=", 1)
            home = Path(value.strip())
            return [home / ("python.exe" if sys.platform == "win32" else "python")]
    except OSError:
        return []
    return []


def _resolve_python_candidate(candidate: Path) -> Path | None:
    if candidate.exists():
        return candidate.resolve()
    if candidate.is_dir():
        nested = candidate / ("python.exe" if sys.platform == "win32" else "python")
        if nested.exists():
            return nested.resolve()
    return None


def _root_files_to_copy(home: Path) -> list[Path]:
    selected: list[Path] = []
    for path in home.iterdir():
        if path.is_file() and (path.name == "LICENSE.txt" or path.suffix.lower() in {".dll", ".exe"}):
            selected.append(path)
    return selected


def _directories_to_copy(home: Path) -> list[Path]:
    return [path for name in ("DLLs", "Lib", "libs", "tcl") if (path := home / name).exists()]


def _copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    directory_path = Path(directory)
    for name in names:
        child = directory_path / name
        if name == "__pycache__" or (child.is_file() and child.suffix.lower() in {".pyc", ".pyo"}):
            ignored.add(name)
        elif directory_path.name == "Lib" and name in {"site-packages", "test", "tests"}:
            ignored.add(name)
    return ignored
