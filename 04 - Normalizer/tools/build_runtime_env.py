from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from runtime_manifest_requirements import runtime_required_files

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_MANIFEST = PROJECT_ROOT / "module-manifest.json"
RUNTIME_MANIFEST = PROJECT_ROOT / "runtime" / "runtime-manifest.json"
RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "python"
VENDOR_PYTHON_ZIP = PROJECT_ROOT / "vendor" / "python" / "cpython-3.11.9-win_amd64.zip"
RUNTIME_WHEELHOUSE = PROJECT_ROOT / "runtime" / "wheelhouse"
RUNTIME_LOCKFILE = PROJECT_ROOT / "runtime" / "requirements.lock.txt"
DEV_WHEELHOUSE = PROJECT_ROOT / "dev-tests" / "wheelhouse"
DEV_LOCKFILE = PROJECT_ROOT / "dev-tests" / "requirements.lock.txt"
HEADLESS_RUNTIME_PATHS = (
    Path("tcl"),
    Path("DLLs") / "tcl86t.dll",
    Path("DLLs") / "tk86t.dll",
    Path("DLLs") / "_tkinter.pyd",
    Path("Lib") / "tkinter",
    Path("Lib") / "idlelib",
    Path("Lib") / "turtledemo",
)


@dataclass(frozen=True)
class BuildTarget:
    name: str
    target_dir: Path
    lockfile: Path
    wheelhouses: tuple[Path, ...]

    @property
    def python_exe(self) -> Path:
        return self.target_dir / "python.exe"


RUNTIME_TARGET = BuildTarget("runtime", RUNTIME_ROOT, RUNTIME_LOCKFILE, (RUNTIME_WHEELHOUSE,))
DEV_TARGET = BuildTarget("dev", PROJECT_ROOT / "dev-tests" / ".venv", DEV_LOCKFILE, (DEV_WHEELHOUSE,))


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _pip_command(python_exe: Path, *args: str) -> list[str]:
    return [str(python_exe), "-m", "pip", "--disable-pip-version-check", *args]


def _python_path_file_name(target_dir: Path) -> str:
    for candidate in target_dir.glob("python*._pth"):
        return candidate.name
    for candidate in sorted(target_dir.glob("python*.dll")):
        suffix = candidate.stem.removeprefix("python")
        if suffix.isdigit():
            return f"python{suffix}._pth"
    return "python311._pth"


def write_python_path_file(target_dir: Path) -> None:
    path_file = target_dir / _python_path_file_name(target_dir)
    lines = [entry for entry in (".", "DLLs", "Lib", r"Lib\site-packages") if (target_dir / entry).exists()]
    lines.append("import site")
    path_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clean_host_binding_files(target_dir: Path) -> None:
    for pattern in ("pyvenv.cfg", "orig-prefix.txt"):
        for candidate in target_dir.rglob(pattern):
            candidate.unlink(missing_ok=True)


def _remove_path(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
        return
    target.unlink(missing_ok=True)


def finalize_runtime_layout(target_dir: Path) -> None:
    if not target_dir.exists():
        return
    for relative_path in HEADLESS_RUNTIME_PATHS:
        _remove_path(target_dir / relative_path)


def _extract_portable_python(target_dir: Path, *, clean: bool) -> None:
    if not VENDOR_PYTHON_ZIP.exists():
        raise FileNotFoundError(f"Portable Python-Basis fehlt: {VENDOR_PYTHON_ZIP}")
    if clean and target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(VENDOR_PYTHON_ZIP) as archive:
        archive.extractall(target_dir)
    (target_dir / "Scripts").mkdir(exist_ok=True)
    _clean_host_binding_files(target_dir)
    write_python_path_file(target_dir)


def _ensure_offline_inputs(target: BuildTarget) -> None:
    if not target.lockfile.exists():
        raise FileNotFoundError(f"Lockfile fehlt: {target.lockfile}")
    for wheelhouse in target.wheelhouses:
        if not wheelhouse.exists():
            raise FileNotFoundError(f"Wheelhouse fehlt: {wheelhouse}")
        if not any(wheelhouse.glob("*.whl")):
            raise FileNotFoundError(f"Wheelhouse ist leer: {wheelhouse}")


def build_target(target: BuildTarget, *, clean: bool) -> None:
    _ensure_offline_inputs(target)
    _extract_portable_python(target.target_dir, clean=clean)
    if not target.python_exe.exists():
        raise FileNotFoundError(f"Portable Python fehlt nach Extraktion: {target.python_exe}")
    _run([str(target.python_exe), "-c", "import sys; print(sys.version)"])
    try:
        _run(_pip_command(target.python_exe, "--version"))
    except subprocess.CalledProcessError:
        _run([str(target.python_exe), "-m", "ensurepip", "--upgrade", "--default-pip"])
        _run(_pip_command(target.python_exe, "--version"))
    install_cmd = _pip_command(target.python_exe, "install", "--no-index", "--upgrade", "--force-reinstall")
    for wheelhouse in target.wheelhouses:
        install_cmd.extend(["--find-links", str(wheelhouse)])
    install_cmd.extend(["-r", str(target.lockfile)])
    _run(install_cmd)
    if target.name == "runtime":
        finalize_runtime_layout(target.target_dir)


def _launcher_package_name() -> str:
    package_name = str(json.loads(MODULE_MANIFEST.read_text(encoding="utf-8")).get("launcher_module") or "").strip()
    if not package_name:
        raise ValueError(f"launcher_module fehlt in {MODULE_MANIFEST}")
    return package_name


def runtime_manifest_payload(package_name: str) -> dict[str, object]:
    return {
        "python_version": "3.11",
        "runtime_candidates": {
            "python": [
                "runtime/python/python.exe",
                "runtime/python/Scripts/python.exe",
                "runtime/python/bin/python",
            ]
        },
        "required_files": runtime_required_files(package_name),
    }


def write_runtime_manifest() -> None:
    finalize_runtime_layout(RUNTIME_ROOT)
    payload = runtime_manifest_payload(_launcher_package_name())
    RUNTIME_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
