from __future__ import annotations

import shutil
from pathlib import Path

from portable_runtime import (
    archive_wheelhouse as archive_wheelhouse_dir,
    ensure_portable_runtime,
    pip_command,
    runtime_python,
    site_packages_dir,
    wheelhouse_archive_path,
)
from runtime_build_config import PIPELINE_ROOT, ModuleBuildTarget, has_runtime_packages
from runtime_build_process import portable_runtime_env, run
from runtime_build_records import prune_runtime_bytecode, resolve_required_wheels, write_lockfile
from runtime_build_validation import validate_runtime_paths


def materialize_required_wheelhouse(target: ModuleBuildTarget) -> None:
    from portable_runtime import materialize_wheelhouse

    materialize_wheelhouse(target.wheelhouse_dir)
    if not target.wheelhouse_dir.exists() or not any(target.wheelhouse_dir.glob("*.whl")):
        archive_path = wheelhouse_archive_path(target.wheelhouse_dir)
        raise FileNotFoundError(f"Offline-Wheelhouse fehlt fuer {target.root.name}: {target.wheelhouse_dir} (Archiv: {archive_path})")


def install_orchestrator_requirements(base_python: Path, target: ModuleBuildTarget, *, run_fn=run) -> None:
    site_packages = site_packages_dir(target.runtime_dir)
    if site_packages.exists():
        shutil.rmtree(site_packages, ignore_errors=True)
    site_packages.mkdir(parents=True, exist_ok=True)
    run_fn(pip_command(base_python, "install", "--ignore-installed", "--no-index", "--only-binary=:all:", "--no-compile", "--target", str(site_packages), "--find-links", str(target.wheelhouse_dir), "-r", str(target.requirements_path)), cwd=target.root)
    prune_runtime_bytecode(target.runtime_dir)


def prune_orchestrator_wheelhouse(target: ModuleBuildTarget, required_wheels: set[str]) -> None:
    if required_wheels:
        for wheel_path in target.wheelhouse_dir.glob("*.whl"):
            if wheel_path.name not in required_wheels:
                wheel_path.unlink(missing_ok=True)


def sanity_check_orchestrator_runtime(target: ModuleBuildTarget, *, run_fn=run, env_fn=portable_runtime_env, runtime_python_fn=runtime_python) -> None:
    run_fn(
        [str(runtime_python_fn(target.runtime_dir)), "-c", "import importlib.metadata as metadata; import customtkinter; import tkinter; import orchestrator; expected = {'customtkinter', 'darkdetect', 'packaging'}; present = {dist.metadata.get('Name', '').lower() for dist in metadata.distributions()}; missing = sorted(expected - present); assert not missing, f'Fehlende Runtime-Pakete: {missing}'"],
        cwd=target.root,
        env=env_fn(target.runtime_dir),
    )


def build_orchestrator_runtime(
    target: ModuleBuildTarget,
    *,
    clean: bool,
    archive_wheelhouse: bool,
    requested_python: str | None,
    resolve_python,
    ensure_pip,
    prepare_runtime,
    sanity_check=sanity_check_orchestrator_runtime,
) -> None:
    base_python = resolve_python(requested_python)
    ensure_pip(base_python)
    python_exe = prepare_runtime(target, base_python=base_python, clean=clean, with_pip=False)
    if has_runtime_packages(target.requirements_path):
        materialize_required_wheelhouse(target)
        prune_orchestrator_wheelhouse(target, resolve_required_wheels(base_python, target))
        install_orchestrator_requirements(base_python, target)
        if archive_wheelhouse:
            archive_wheelhouse_dir(target.wheelhouse_dir, prune=True)
    else:
        shutil.rmtree(target.wheelhouse_dir, ignore_errors=True)
        wheelhouse_archive_path(target.wheelhouse_dir).unlink(missing_ok=True)
    sanity_check(target)
    write_lockfile(python_exe, target)
    ensure_portable_runtime(target.runtime_dir)


def validate_orchestrator_runtime(target: ModuleBuildTarget, *, sanity_check=sanity_check_orchestrator_runtime) -> None:
    ensure_portable_runtime(target.runtime_dir)
    validate_runtime_paths(target)
    sanity_check(target)
