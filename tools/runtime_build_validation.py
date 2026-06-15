from __future__ import annotations

import json
from pathlib import Path

from portable_runtime import runtime_python, site_packages_dir
from runtime_build_config import ModuleBuildTarget
from runtime_build_process import portable_runtime_env, run
from runtime_build_records import (
    runtime_validation_modules,
    validate_offline_dependency_install,
    validate_runtime_record_files,
    validate_wheelhouse_against_lockfile,
)


def validate_module_runtime(target: ModuleBuildTarget, *, base_python: Path) -> None:
    validate_wheelhouse_against_lockfile(target)
    validate_runtime_paths(target)
    validate_runtime_record_files(target)
    validate_runtime_imports(target)
    validate_runtime_tk(target)
    validate_runtime_cli(target)
    validate_offline_dependency_install(base_python, target)


def validate_runtime_paths(target: ModuleBuildTarget, *, run_fn=run, env_fn=portable_runtime_env) -> None:
    completed = run_fn(
        [str(runtime_python(target.runtime_dir)), "-c", "import json, sysconfig; print(json.dumps({k: sysconfig.get_path(k) for k in ['stdlib', 'platstdlib', 'purelib', 'scripts']}, ensure_ascii=True))"],
        cwd=target.root,
        env=env_fn(target.runtime_dir),
        capture_output=True,
    )
    runtime_root = str(target.runtime_dir.resolve()).lower()
    leaking = _external_runtime_paths(json.loads(completed.stdout), runtime_root)
    if leaking:
        raise RuntimeError("Runtime verweist noch auf externe Stdlib-/Scripts-Pfade:\n" + "\n".join(f"- {entry}" for entry in leaking))


def validate_runtime_imports(target: ModuleBuildTarget, *, run_fn=run, env_fn=portable_runtime_env) -> None:
    imports = runtime_validation_modules(target)
    if imports:
        run_fn([str(runtime_python(target.runtime_dir)), "-c", f"import {', '.join(imports)}"], cwd=target.root, env=env_fn(target.runtime_dir))


def validate_runtime_tk(target: ModuleBuildTarget, *, run_fn=run, env_fn=portable_runtime_env) -> None:
    if "customtkinter" not in runtime_validation_modules(target):
        return
    _validate_tk_files(target)
    completed = run_fn(
        [str(runtime_python(target.runtime_dir)), "-c", "import json, os, tkinter, _tkinter; print(json.dumps({'tkinter': tkinter.__file__, '_tkinter': _tkinter.__file__, 'tcl_version': getattr(_tkinter, 'TCL_VERSION', ''), 'tk_version': getattr(_tkinter, 'TK_VERSION', ''), 'tcl_library': os.environ.get('TCL_LIBRARY', ''), 'tk_library': os.environ.get('TK_LIBRARY', '')}, ensure_ascii=True))"],
        cwd=target.root,
        env=env_fn(target.runtime_dir),
        capture_output=True,
    )
    _validate_tk_payload(json.loads(completed.stdout), runtime_root=str(target.runtime_dir.resolve()).lower())


def validate_runtime_cli(target: ModuleBuildTarget, *, run_fn=run, env_fn=portable_runtime_env) -> None:
    package_name = target.package_name
    if package_name and (target.root / package_name / "__main__.py").exists():
        run_fn([str(runtime_python(target.runtime_dir)), "-m", package_name, "--help"], cwd=target.root, env=env_fn(target.runtime_dir))


def validate_client_frontend_bundle(target: ModuleBuildTarget, *, run_fn=run) -> None:
    if not target.is_client_frontend:
        return
    node_exe = target.root / "node" / "node.exe"
    checker = target.root / "tools" / "check-runtimes.mjs"
    if not node_exe.exists():
        raise FileNotFoundError(f"Bundled Node fehlt: {node_exe}")
    if not checker.exists():
        raise FileNotFoundError(f"Frontend-Runtime-Checker fehlt: {checker}")
    run_fn([str(node_exe), "--disable-warning=ExperimentalWarning", str(checker)], cwd=target.root)


def _external_runtime_paths(layout: dict[str, object], runtime_root: str) -> list[str]:
    leaking: list[str] = []
    for key, value in layout.items():
        if isinstance(value, str) and not str(Path(value).resolve()).lower().startswith(runtime_root):
            leaking.append(f"{key}={value}")
    return leaking


def _validate_tk_files(target: ModuleBuildTarget) -> None:
    required_paths = (
        target.runtime_dir / "tcl" / "tcl8.6" / "init.tcl",
        target.runtime_dir / "tcl" / "tk8.6" / "tk.tcl",
        target.runtime_dir / "DLLs" / "tcl86t.dll",
        target.runtime_dir / "DLLs" / "tk86t.dll",
    )
    if missing := [str(path) for path in required_paths if not path.exists()]:
        raise FileNotFoundError("Tcl/Tk fehlt in der Runtime:\n" + "\n".join(f"- {path}" for path in missing))


def _validate_tk_payload(payload: dict[str, object], *, runtime_root: str) -> None:
    for key in ("tkinter", "_tkinter"):
        resolved = str(Path(str(payload[key])).resolve()).lower()
        if not resolved.startswith(runtime_root):
            raise RuntimeError(f"{key} wird nicht aus der Runtime geladen: {payload[key]}")
    for key in ("tcl_library", "tk_library"):
        value = str(payload.get(key, "")).strip()
        if not value:
            raise RuntimeError(f"{key} ist in der Runtime-Umgebung nicht gesetzt.")
        if not str(Path(value).resolve()).lower().startswith(runtime_root):
            raise RuntimeError(f"{key} verweist nicht auf die Runtime: {value}")
    if not payload.get("tcl_version") or not payload.get("tk_version"):
        raise RuntimeError("Tkinter meldet keine Tcl/Tk-Version aus der Runtime.")
