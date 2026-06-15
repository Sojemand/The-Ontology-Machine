from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path


def remove_tree(path: Path) -> None:
    def _onerror(func, target, _exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    for attempt in range(5):
        try:
            shutil.rmtree(path, onerror=_onerror)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5 * (attempt + 1))


def copy_runtime_tree(source_dir: Path, target_dir: Path, *, clean: bool) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"Runtime-Basis fehlt: {source_dir}")
    if clean and target_dir.exists():
        remove_tree(target_dir)
    if target_dir.exists():
        remove_tree(target_dir)
    shutil.copytree(
        source_dir,
        target_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def clean_host_binding_files(target_dir: Path) -> None:
    for pattern in ("pyvenv.cfg", "orig-prefix.txt"):
        for candidate in target_dir.rglob(pattern):
            candidate.unlink(missing_ok=True)


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)
