from __future__ import annotations

import os
import subprocess
from pathlib import Path

from installer_stage_process import run


def find_iscc(pipeline_root: Path) -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    try:
        completed = run(["where.exe", "ISCC.exe"], cwd=pipeline_root)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    for raw_line in completed.stdout.splitlines():
        candidate = Path(raw_line.strip())
        if candidate.exists():
            return candidate
    return None


def compile_installer(
    pipeline_root: Path,
    module_root: Path,
    staging_dir: Path,
    output_dir: Path,
    *,
    app_version: str,
    script_name: str,
) -> Path:
    script_path = module_root / "installer" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Inno-Setup-Skript fehlt: {script_path}")
    iscc = find_iscc(pipeline_root)
    if iscc is None:
        raise FileNotFoundError("ISCC.exe wurde nicht gefunden. Inno Setup 6 ist nicht installiert.")
    output_dir.mkdir(parents=True, exist_ok=True)
    run([str(iscc), f"/DSourceDir={staging_dir}", f"/DOutputDir={output_dir}", f"/DAppVersion={app_version}", str(script_path)], cwd=module_root)
    return output_dir
