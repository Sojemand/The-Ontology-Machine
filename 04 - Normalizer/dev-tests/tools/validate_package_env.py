from __future__ import annotations

import json
import subprocess
from pathlib import Path

from validate_package_policy import (
    PROJECT_ROOT,
    SKIP_DIR_NAMES,
    EnvironmentSpec,
    canonicalize_name,
    parse_lockfile,
    parse_wheelhouse,
    scan_text_files,
)


def load_installed_distributions(python_exe: Path) -> dict[str, str]:
    command = [
        str(python_exe),
        "-c",
        (
            "import importlib.metadata as m, json; "
            "payload = {dist.metadata['Name']: dist.version for dist in m.distributions() if dist.metadata.get('Name')}; "
            "print(json.dumps(payload, sort_keys=True))"
        ),
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True, encoding="utf-8")
    raw = json.loads(completed.stdout)
    return {canonicalize_name(name): version for name, version in raw.items()}


def validate_environment(spec: EnvironmentSpec) -> list[str]:
    issues: list[str] = []
    if not spec.root.exists():
        return [f"{spec.name}: Umgebung fehlt: {spec.root}"]
    if (spec.root / "pyvenv.cfg").exists():
        issues.append(f"{spec.name}: pyvenv.cfg darf nicht vorhanden sein")
    if not spec.python_exe.exists():
        issues.append(f"{spec.name}: python.exe fehlt")
        return issues
    issues.extend(_validate_wheels(spec))
    installed = _safe_installed_distributions(spec, issues)
    if installed is None:
        return issues
    for package_name, version in parse_lockfile(spec.lockfile).items():
        if installed.get(package_name) != version:
            issues.append(
                f"{spec.name}: installierte Version abweichend fuer {package_name}: "
                f"{installed.get(package_name, '<missing>')} != {version}"
            )
    issues.extend(_run_import_smoke(spec))
    issues.extend(scan_text_files(spec.root, skip_dir_names=SKIP_DIR_NAMES))
    return issues


def _validate_wheels(spec: EnvironmentSpec) -> list[str]:
    issues: list[str] = []
    available_wheels: dict[str, str] = {}
    for wheelhouse in spec.wheelhouses:
        if not wheelhouse.exists():
            issues.append(f"{spec.name}: Wheelhouse fehlt: {wheelhouse}")
            continue
        available_wheels.update(parse_wheelhouse(wheelhouse))
    for package_name, version in parse_lockfile(spec.lockfile).items():
        if available_wheels.get(package_name) != version:
            issues.append(f"{spec.name}: Wheelhouse fehlt fuer {package_name}=={version}")
    return issues


def _safe_installed_distributions(spec: EnvironmentSpec, issues: list[str]) -> dict[str, str] | None:
    try:
        return load_installed_distributions(spec.python_exe)
    except subprocess.CalledProcessError as exc:
        issues.append(f"{spec.name}: installierte Distributionen konnten nicht gelesen werden: {exc}")
        return None


def _run_import_smoke(spec: EnvironmentSpec) -> list[str]:
    try:
        subprocess.run(
            [str(spec.python_exe), "-c", _import_smoke_script(spec)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        return [f"{spec.name}: Import-Smoke-Test fehlgeschlagen: {exc.stderr.strip() or exc.stdout.strip()}"]
    return []


def _import_smoke_script(spec: EnvironmentSpec) -> str:
    modules = ["requests", "yaml", "normalizer_vision"]
    if spec.name == "dev":
        modules.extend(["pytest", "py"])
    return "import pathlib, sys; sys.path.insert(0, str(pathlib.Path.cwd())); import " + ", ".join(modules)
