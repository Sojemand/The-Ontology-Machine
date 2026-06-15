from __future__ import annotations

import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from portable_runtime import (
    materialize_wheelhouse,
    pip_command,
    runtime_python,
    site_packages_dir,
    wheelhouse_archive_path,
)
from runtime_build_config import (
    PIN_RE,
    VALIDATION_IMPORT_MAP,
    ModuleBuildTarget,
    has_runtime_packages,
    normalize_dist_name,
)
from runtime_build_process import portable_runtime_env, run


def write_lockfile(python_exe: Path, target: ModuleBuildTarget, *, run_fn=run, env_fn=portable_runtime_env) -> None:
    completed = _orchestrator_lockfile_output(python_exe, target, run_fn=run_fn, env_fn=env_fn) if target.is_orchestrator else run_fn(
        pip_command(python_exe, "freeze"),
        cwd=target.root,
        env=env_fn(target.runtime_dir),
        capture_output=True,
    )
    target.lockfile_path.parent.mkdir(parents=True, exist_ok=True)
    target.lockfile_path.write_text(completed.stdout if not target.is_orchestrator else _normalized_stdout(completed), encoding="utf-8")


def read_pinned_requirements(lockfile_path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    if not lockfile_path.exists():
        return pins
    for raw_line in lockfile_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and (match := PIN_RE.match(line)):
            name, version = match.groups()
            pins[normalize_dist_name(name)] = version
    return pins


def runtime_validation_modules(target: ModuleBuildTarget) -> list[str]:
    pins = read_pinned_requirements(target.lockfile_path)
    modules: list[str] = []
    for package_name, module_name in VALIDATION_IMPORT_MAP.items():
        if package_name in pins and module_name not in modules:
            modules.append(module_name)
    return modules


def validate_runtime_record_files(target: ModuleBuildTarget) -> None:
    site_packages = site_packages_dir(target.runtime_dir)
    if not site_packages.exists():
        return
    missing = _missing_record_files(site_packages)
    if missing:
        preview = "\n".join(f"- {entry}" for entry in missing[:20])
        suffix = "\n- ..." if len(missing) > 20 else ""
        raise FileNotFoundError("Runtime enthaelt laut RECORD fehlende Dateien:\n" f"{preview}{suffix}")


def validate_wheelhouse_against_lockfile(target: ModuleBuildTarget) -> None:
    if not has_runtime_packages(target.requirements_path):
        return
    wheelhouse_dir = materialize_wheelhouse(target.wheelhouse_dir)
    if not wheelhouse_dir.exists() or not any(wheelhouse_dir.glob("*.whl")):
        raise FileNotFoundError(f"Wheelhouse fehlt oder ist leer: {target.wheelhouse_dir}")
    versions = wheelhouse_versions(wheelhouse_dir)
    missing = [f"{name}=={version}" for name, version in read_pinned_requirements(target.lockfile_path).items() if version not in versions.get(name, set())]
    if missing:
        raise FileNotFoundError("Wheelhouse deckt das Lockfile nicht vollstaendig ab:\n" + "\n".join(f"- {entry}" for entry in missing))


def validate_offline_dependency_install(base_python: Path, target: ModuleBuildTarget, *, run_fn=run) -> None:
    if not has_runtime_packages(target.requirements_path):
        return
    wheelhouse_dir = materialize_wheelhouse(target.wheelhouse_dir)
    with tempfile.TemporaryDirectory(prefix="vision-pipeline-offline-install-") as tmp_dir:
        venv_dir = Path(tmp_dir) / "venv"
        run_fn([str(base_python), "-m", "venv", "--clear", str(venv_dir)], cwd=target.root)
        venv_python = runtime_python(venv_dir)
        run_fn(pip_command(venv_python, "install", "--no-index", "--find-links", str(wheelhouse_dir), "-r", str(target.lockfile_path)), cwd=target.root)
        if imports := runtime_validation_modules(target):
            run_fn([str(venv_python), "-c", f"import {', '.join(imports)}"], cwd=target.root)


def prune_runtime_bytecode(runtime_dir: Path) -> None:
    for cache_dir in runtime_dir.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)
    for pattern in ("*.pyc", "*.pyo"):
        for compiled_path in runtime_dir.rglob(pattern):
            compiled_path.unlink(missing_ok=True)


def wheelhouse_versions(wheelhouse_dir: Path) -> dict[str, set[str]]:
    versions: dict[str, set[str]] = {}
    for wheel_path in wheelhouse_dir.glob("*.whl"):
        parts = wheel_path.name.split("-")
        if len(parts) >= 2:
            versions.setdefault(normalize_dist_name(parts[0]), set()).add(parts[1])
    return versions


def resolve_required_wheels(base_python: Path, target: ModuleBuildTarget, *, run_fn=run) -> set[str]:
    with tempfile.TemporaryDirectory(prefix="vision-pipeline-wheel-report-") as tmp_dir:
        report_path = Path(tmp_dir) / "report.json"
        run_fn(pip_command(base_python, "install", "--dry-run", "--ignore-installed", "--no-index", "--only-binary=:all:", "--target", str(site_packages_dir(target.runtime_dir)), "--report", str(report_path), "--find-links", str(target.wheelhouse_dir), "-r", str(target.requirements_path)), cwd=target.root)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    return _wheel_names_from_report(payload)


def _orchestrator_lockfile_output(python_exe: Path, target: ModuleBuildTarget, *, run_fn, env_fn):
    return run_fn(
        [str(python_exe), "-c", "import importlib.metadata as metadata; lines = [f\"{name}=={dist.version}\" for dist in sorted(metadata.distributions(), key=lambda item: item.metadata.get('Name', '').lower()) for name in [(dist.metadata.get('Name') or '').strip()] if name]; print('\\n'.join(lines))"],
        cwd=target.root,
        env=env_fn(target.runtime_dir),
        capture_output=True,
    )


def _normalized_stdout(completed) -> str:
    output = completed.stdout.strip()
    return f"{output}\n" if output else ""


def _missing_record_files(site_packages: Path) -> list[str]:
    missing: list[str] = []
    for record_path in site_packages.glob("*.dist-info/RECORD"):
        try:
            rows = csv.reader(record_path.read_text(encoding="utf-8").splitlines())
        except OSError:
            continue
        for row in rows:
            _append_missing_record_file(missing, site_packages, record_path, row)
    return missing


def _append_missing_record_file(missing: list[str], site_packages: Path, record_path: Path, row: list[str]) -> None:
    if not row or not (raw_relative := str(row[0]).strip()):
        return
    relative_path = Path(raw_relative)
    if relative_path.is_absolute() or ".." in relative_path.parts or "__pycache__" in relative_path.parts or relative_path.suffix.lower() in {".pyc", ".pyo"}:
        return
    if not (site_packages / relative_path).exists():
        missing.append(f"{record_path.parent.name}: {raw_relative}")


def _wheel_names_from_report(payload: dict[str, Any]) -> set[str]:
    wheel_names: set[str] = set()
    for entry in payload.get("install", []):
        if isinstance(entry, dict) and isinstance(download_info := entry.get("download_info", {}), dict):
            if raw_url := str(download_info.get("url", "")).strip():
                wheel_names.add(Path(unquote(urlparse(raw_url).path)).name)
    return wheel_names
