from __future__ import annotations

import os
import shutil
from pathlib import Path

from runtime_build_config import LIBREOFFICE_BUILD_HOME_ENV, ModuleBuildTarget
from runtime_build_process import run


def normalize_libreoffice_root(candidate: Path) -> Path | None:
    if candidate.is_file() and candidate.name.lower() == "soffice.exe":
        return candidate.parent.parent
    if candidate.is_dir() and candidate.name.lower() == "program" and (candidate / "soffice.exe").exists():
        return candidate.parent
    if candidate.is_dir() and (candidate / "program" / "soffice.exe").exists():
        return candidate
    return None


def libreoffice_source_candidates() -> list[Path]:
    candidates: list[Path] = []
    if override := os.environ.get(LIBREOFFICE_BUILD_HOME_ENV, "").strip():
        candidates.append(Path(override))
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        if root := os.environ.get(env_name, "").strip():
            candidates.append(Path(root) / "LibreOffice")
    return candidates


def resolve_libreoffice_source_root() -> Path:
    for candidate in libreoffice_source_candidates():
        if normalized := normalize_libreoffice_root(candidate):
            return normalized
    raise FileNotFoundError(
        "Keine lokale LibreOffice-Installation fuer den Runtime-Build gefunden. "
        f"Setze optional {LIBREOFFICE_BUILD_HOME_ENV} auf den LibreOffice-Ordner."
    )


def validate_bundled_libreoffice(target: ModuleBuildTarget, *, run_fn=run) -> None:
    soffice = target.libreoffice_cli
    if not soffice.exists():
        raise FileNotFoundError(f"Bundled LibreOffice fehlt: {soffice}")
    run_fn([str(soffice), "--version"], cwd=target.root, capture_output=True)


def build_bundled_libreoffice_runtime(
    target: ModuleBuildTarget,
    *,
    clean: bool,
    validate_only: bool,
    run_fn=run,
    resolve_source_root=resolve_libreoffice_source_root,
) -> None:
    if not target.bundles_libreoffice:
        return
    if validate_only:
        validate_bundled_libreoffice(target, run_fn=run_fn)
        return
    if target.libreoffice_dir.exists():
        if clean:
            shutil.rmtree(target.libreoffice_dir, ignore_errors=True)
        else:
            validate_bundled_libreoffice(target, run_fn=run_fn)
            return
    shutil.copytree(resolve_source_root(), target.libreoffice_dir)
    validate_bundled_libreoffice(target, run_fn=run_fn)
