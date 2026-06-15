"""Boundary helpers for plugin filesystem and subprocess runtime I/O."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from . import debug, validation


def plugin_dir(registry, name: str) -> Path:
    return registry._dir / name


def load_manifest(plugin_dir: Path, fallback_name: str):
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return validation.build_manifest(data, fallback_name)
    except Exception as exc:
        debug.log_manifest_load_failed(plugin_dir, exc)
        return None


def bundled_python_candidates(registry) -> tuple[Path, ...]:
    ext = ".exe" if sys.platform == "win32" else ""
    runtime_root = registry._layout.runtime_dir / "python"
    return (
        runtime_root / f"python{ext}",
        runtime_root / "Scripts" / f"python{ext}",
        runtime_root / "bin" / "python",
    )


def resolve_python(registry) -> Path:
    for candidate in bundled_python_candidates(registry):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"File-Profil: gebuendelte Modul-Runtime fehlt oder ist beschaedigt. Erwartet unter {registry._layout.runtime_dir / 'python'}"
    )


def plugin_runtime_root(registry, name: str) -> Path:
    return registry._plugin_dir(name) / "runtime" / "python"


def plugin_bundled_python_candidates(registry, name: str) -> tuple[Path, ...]:
    ext = ".exe" if sys.platform == "win32" else ""
    runtime_root = plugin_runtime_root(registry, name)
    return (
        runtime_root / f"python{ext}",
        runtime_root / "Scripts" / f"python{ext}",
        runtime_root / "bin" / "python",
    )


def ensure_plugin_runtime(registry, name: str) -> Path:
    runtime_root = plugin_runtime_root(registry, name)
    for candidate in plugin_bundled_python_candidates(registry, name):
        if candidate.exists():
            validation.validate_runtime_root(runtime_root, name)
            return candidate
    raise FileNotFoundError(
        f"Extractor {name}: gebuendelte Runtime fehlt oder ist beschaedigt. Erwartet unter {runtime_root}"
    )


def resolve_plugin_python(registry, name: str) -> Path:
    runtime_root = plugin_runtime_root(registry, name)
    if runtime_root.exists():
        return ensure_plugin_runtime(registry, name)
    return resolve_python(registry)


def subprocess_env(registry) -> dict[str, str]:
    runtime_root = registry._layout.runtime_dir / "python"
    python_path = resolve_python(registry)
    if python_path.parent == runtime_root or python_path.parent.parent == runtime_root:
        env = {
            **debug.subprocess_env_defaults(),
            "PYTHONHOME": str(runtime_root),
            "PYTHONPATH": "",
            "PYTHONNOUSERSITE": "1",
        }
        tcl_dir = runtime_root / "tcl"
        if (tcl_dir / "tcl8.6").exists():
            env["TCL_LIBRARY"] = str(tcl_dir / "tcl8.6")
        if (tcl_dir / "tk8.6").exists():
            env["TK_LIBRARY"] = str(tcl_dir / "tk8.6")
        return env
    return debug.subprocess_env_defaults()


def plugin_subprocess_env(registry, name: str) -> dict[str, str]:
    runtime_root = plugin_runtime_root(registry, name)
    if runtime_root.exists():
        ensure_plugin_runtime(registry, name)
        env = {
            **debug.subprocess_env_defaults(),
            "PYTHONHOME": str(runtime_root),
            "PYTHONPATH": "",
            "PYTHONNOUSERSITE": "1",
        }
        tcl_dir = runtime_root / "tcl"
        if (tcl_dir / "tcl8.6").exists():
            env["TCL_LIBRARY"] = str(tcl_dir / "tcl8.6")
        else:
            env.pop("TCL_LIBRARY", None)
        if (tcl_dir / "tk8.6").exists():
            env["TK_LIBRARY"] = str(tcl_dir / "tk8.6")
        else:
            env.pop("TK_LIBRARY", None)
        return env
    return subprocess_env(registry)
