from __future__ import annotations

import shutil
import sys
from pathlib import Path

from portable_runtime import (
    archive_wheelhouse as archive_wheelhouse_dir,
    create_portable_runtime,
    ensure_pip,
    ensure_portable_runtime,
    materialize_wheelhouse,
    pip_command,
    query_python_layout,
    runtime_python,
    wheelhouse_archive_path,
)
from runtime_build_config import PIPELINE_ROOT, TOOLS_DIR, ModuleBuildTarget, has_runtime_packages
from runtime_build_libreoffice import build_bundled_libreoffice_runtime
from runtime_build_process import portable_runtime_env, run
from runtime_build_records import prune_runtime_bytecode, write_lockfile
from runtime_build_validation import validate_client_frontend_bundle, validate_module_runtime


def prepare_portable_runtime(target: ModuleBuildTarget, *, base_python: Path, clean: bool, with_pip: bool) -> Path:
    base_layout = query_python_layout(base_python)
    recreate_runtime = _should_recreate_runtime(target, clean=clean, base_version=base_layout.version_info[:2])
    if recreate_runtime:
        try:
            create_portable_runtime(target.runtime_dir, base_python=base_python, clean=True, with_pip=with_pip)
        except FileNotFoundError:
            if sys.platform != "win32":
                raise
            create_portable_runtime_subprocess(target, base_python=base_python, with_pip=with_pip)
    else:
        ensure_portable_runtime(target.runtime_dir)
        if with_pip:
            ensure_pip(target.runtime_dir)
    python_exe = runtime_python(target.runtime_dir)
    if not python_exe.exists():
        raise FileNotFoundError(f"Bundled Python fehlt nach Build: {python_exe}")
    return python_exe


def build_default_runtime(
    target: ModuleBuildTarget,
    *,
    clean: bool,
    offline: bool,
    refresh_wheelhouse: bool,
    archive_wheelhouse: bool,
    requested_python: str | None,
    validate_only: bool,
    resolve_python,
) -> None:
    if refresh_wheelhouse and offline:
        raise ValueError("--refresh-wheelhouse und --offline koennen nicht kombiniert werden.")
    base_python = resolve_python(requested_python, purpose=f"{target.root.name}-Runtime")
    if validate_only:
        ensure_portable_runtime(target.runtime_dir)
        validate_module_runtime(target, base_python=base_python)
        return
    python_exe = prepare_portable_runtime(target, base_python=base_python, clean=clean, with_pip=True)
    runtime_env = portable_runtime_env(target.runtime_dir)
    run(pip_command(python_exe, "--version"), cwd=target.root, env=runtime_env)
    if has_runtime_packages(target.requirements_path):
        _prepare_and_install_requirements(target, base_python, python_exe, runtime_env, refresh_wheelhouse)
        write_lockfile(python_exe, target)
        validate_module_runtime(target, base_python=base_python)
        if archive_wheelhouse:
            archive_wheelhouse_dir(target.wheelhouse_dir, prune=True)
    else:
        _clear_wheelhouse(target)
        write_lockfile(python_exe, target)
        validate_module_runtime(target, base_python=base_python)
    prune_runtime_bytecode(target.runtime_dir)
    ensure_portable_runtime(target.runtime_dir)


def build_client_frontend_runtime(target: ModuleBuildTarget, **kwargs) -> None:
    build_default_runtime(target, **kwargs)
    validate_client_frontend_bundle(target)


def create_portable_runtime_subprocess(target: ModuleBuildTarget, *, base_python: Path, with_pip: bool) -> None:
    script = (
        "from pathlib import Path; import sys; "
        f"sys.path.insert(0, {str(TOOLS_DIR)!r}); "
        "from portable_runtime import create_portable_runtime; "
        "create_portable_runtime(Path(sys.argv[1]), base_python=Path(sys.argv[2]), clean=True, with_pip=sys.argv[3] == '1')"
    )
    run([str(Path(sys.executable).resolve()), "-c", script, str(target.runtime_dir), str(base_python), "1" if with_pip else "0"], cwd=PIPELINE_ROOT)


def _should_recreate_runtime(target: ModuleBuildTarget, *, clean: bool, base_version: tuple[int, int]) -> bool:
    if clean or not target.runtime_dir.exists():
        return True
    try:
        ensure_portable_runtime(target.runtime_dir)
        existing_layout = query_python_layout(runtime_python(target.runtime_dir))
    except Exception:
        return True
    return existing_layout.version_info[:2] != base_version


def _prepare_and_install_requirements(target: ModuleBuildTarget, base_python: Path, python_exe: Path, runtime_env: dict[str, str], refresh_wheelhouse: bool) -> None:
    archive_path = wheelhouse_archive_path(target.wheelhouse_dir)
    if refresh_wheelhouse:
        shutil.rmtree(target.wheelhouse_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        target.wheelhouse_dir.mkdir(parents=True, exist_ok=True)
        run(pip_command(base_python, "wheel", "-r", str(target.requirements_path), "-w", str(target.wheelhouse_dir)), cwd=target.root)
    else:
        materialize_wheelhouse(target.wheelhouse_dir)
        if not target.wheelhouse_dir.exists() or not any(target.wheelhouse_dir.glob("*.whl")):
            raise FileNotFoundError(f"Interne Wheelhouse fehlt: {target.wheelhouse_dir}. Nutze --refresh-wheelhouse nur zum absichtlichen Neubau.")
    run(pip_command(python_exe, "install", "--upgrade", "--force-reinstall", "--no-index", "--no-compile", "--find-links", str(target.wheelhouse_dir), "-r", str(target.requirements_path)), cwd=target.root, env=runtime_env)


def _clear_wheelhouse(target: ModuleBuildTarget) -> None:
    shutil.rmtree(target.wheelhouse_dir, ignore_errors=True)
    wheelhouse_archive_path(target.wheelhouse_dir).unlink(missing_ok=True)
