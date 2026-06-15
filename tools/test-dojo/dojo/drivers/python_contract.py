from __future__ import annotations

from pathlib import Path

from ..runtime import CommandResult, run_command


def invoke_contract(python_exe: Path, module: str, request: Path, response: Path, *, cwd: Path) -> CommandResult:
    return run_command(
        [str(python_exe), "-m", module, "--request", str(request), "--response", str(response)],
        cwd=cwd,
    )
