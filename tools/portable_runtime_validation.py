from __future__ import annotations

import sys
from pathlib import Path

from portable_runtime_layout import runtime_python


def runtime_problems(runtime_dir: str | Path) -> list[str]:
    root = Path(runtime_dir)
    problems: list[str] = []
    python_exe = runtime_python(root)
    if not python_exe.exists():
        problems.append(f"python executable missing: {python_exe}")
    if (root / "pyvenv.cfg").exists():
        problems.append("legacy venv marker present")
    if sys.platform == "win32":
        stdlib_root = root / "Lib"
        if not (stdlib_root / "os.py").exists():
            problems.append(f"stdlib missing os.py under {stdlib_root}")
        if not (stdlib_root / "encodings" / "__init__.py").exists():
            problems.append(f"stdlib missing encodings package under {stdlib_root}")
    return problems


def is_portable_runtime(runtime_dir: str | Path) -> bool:
    return not runtime_problems(runtime_dir)


def ensure_portable_runtime(runtime_dir: str | Path) -> None:
    problems = runtime_problems(runtime_dir)
    if problems:
        raise RuntimeError("; ".join(problems))
