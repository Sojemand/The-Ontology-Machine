from __future__ import annotations

import subprocess
from pathlib import Path

from bootstrap_dev_runtime import run


def pip_command(python_exe: Path, *args: str) -> list[str]:
    return [str(python_exe), "-m", "pip", "--disable-pip-version-check", *args]


def run_import_preflight(python_exe: Path, modules: list[str], *, cwd: Path) -> None:
    requested = [name for name in modules if name]
    if not requested:
        return
    run(
        [
            str(python_exe),
            "-c",
            (
                "import importlib, sys\n"
                "failures = []\n"
                "for name in sys.argv[1:]:\n"
                "    try:\n"
                "        importlib.import_module(name)\n"
                "    except Exception as exc:\n"
                "        failures.append(f'{name}: {exc}')\n"
                "if failures:\n"
                "    raise SystemExit('\\n'.join(failures))\n"
            ),
            *requested,
        ],
        cwd=cwd,
    )


def ensure_pip(python_exe: Path, *, cwd: Path) -> None:
    try:
        run(pip_command(python_exe, "--version"), cwd=cwd)
    except subprocess.CalledProcessError:
        run([str(python_exe), "-m", "ensurepip", "--upgrade", "--default-pip"], cwd=cwd)
