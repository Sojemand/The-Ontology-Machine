from __future__ import annotations

import os
from pathlib import Path


def python_candidates(root: Path) -> list[Path]:
    return [
        root / "python.exe",
        root / "Scripts" / "python.exe",
        root / "bin" / "python",
    ]


def resolve_python_exe(target_dir: Path) -> Path:
    for candidate in python_candidates(target_dir):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Kein Python-Interpreter unter {target_dir} gefunden.")


def python_path_file_name(target_dir: Path) -> str:
    for candidate in target_dir.glob("python*._pth"):
        return candidate.name
    for candidate in sorted(target_dir.glob("python*.dll")):
        suffix = candidate.stem.removeprefix("python")
        if suffix.isdigit():
            return f"python{suffix}._pth"
    return "python311._pth"


def write_python_path_file(target_dir: Path) -> None:
    path_file = target_dir / python_path_file_name(target_dir)
    lines: list[str] = []
    for entry in (".", "DLLs", "Lib", r"Lib\site-packages"):
        if (target_dir / entry).exists():
            lines.append(entry)
    lines.append("import site")
    path_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def site_packages_dir(target_dir: Path) -> Path:
    candidates = (
        target_dir / "Lib" / "site-packages",
        target_dir / "lib" / "site-packages",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    fallback = target_dir / "Lib" / "site-packages"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def write_python_path_overlay(target_dir: Path, entries: list[Path]) -> None:
    site_packages = site_packages_dir(target_dir)
    overlay_entries = [str(entry) for entry in entries if entry.exists()]
    if not overlay_entries:
        return
    normalized_entries: list[str] = []
    for entry in entries:
        if not entry.exists():
            continue
        try:
            normalized_entries.append(os.path.relpath(entry, start=site_packages))
        except ValueError:
            normalized_entries.append(str(entry))
    overlay_path = site_packages / "devtests-local.pth"
    overlay_path.write_text("\n".join(normalized_entries) + "\n", encoding="utf-8")
