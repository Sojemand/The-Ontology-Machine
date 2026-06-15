from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    cwd: str
    returncode: int
    stdout: str
    stderr: str


def run_command(args: list[str], *, cwd: Path, timeout_seconds: int = 300, env: dict[str, str] | None = None) -> CommandResult:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
    )
    return CommandResult(
        args=tuple(args),
        cwd=str(cwd),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
