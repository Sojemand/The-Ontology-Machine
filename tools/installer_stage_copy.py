from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path

from installer_stage_filters import robocopy_exclusions, should_skip


def copy_release_tree(
    module_root: Path,
    staging_dir: Path,
    *,
    mutable_dirs: tuple[str, ...],
    mutable_files: tuple[str, ...],
    excluded_runtime_paths: tuple[str, ...],
) -> None:
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        copy_release_tree_with_robocopy(module_root, staging_dir, mutable_dirs=mutable_dirs, mutable_files=mutable_files, excluded_runtime_paths=excluded_runtime_paths)
        return
    copy_release_tree_with_python(module_root, staging_dir, mutable_dirs=mutable_dirs, mutable_files=mutable_files, excluded_runtime_paths=excluded_runtime_paths)


def copy_release_tree_with_python(
    module_root: Path,
    staging_dir: Path,
    *,
    mutable_dirs: tuple[str, ...],
    mutable_files: tuple[str, ...],
    excluded_runtime_paths: tuple[str, ...],
) -> None:
    with mounted_paths(module_root, staging_dir) as (effective_root, effective_stage):
        if effective_stage.exists():
            shutil.rmtree(effective_stage, ignore_errors=True)
        effective_stage.mkdir(parents=True, exist_ok=True)
        for source in effective_root.rglob("*"):
            relative = source.relative_to(effective_root)
            if should_skip(relative, mutable_dirs=mutable_dirs, mutable_files=mutable_files, excluded_runtime_paths=excluded_runtime_paths):
                continue
            destination = effective_stage / relative
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)


def copy_release_tree_with_robocopy(
    module_root: Path,
    staging_dir: Path,
    *,
    mutable_dirs: tuple[str, ...],
    mutable_files: tuple[str, ...],
    excluded_runtime_paths: tuple[str, ...],
) -> None:
    with mounted_paths(module_root, staging_dir) as (effective_root, effective_stage):
        if effective_stage.exists():
            shutil.rmtree(effective_stage, ignore_errors=True)
        effective_stage.mkdir(parents=True, exist_ok=True)
        exclude_dirs, exclude_files = robocopy_exclusions(effective_root, mutable_dirs=mutable_dirs, mutable_files=mutable_files, excluded_runtime_paths=excluded_runtime_paths)
        command = ["robocopy", str(effective_root), str(effective_stage), "/E", "/MT:8", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP"]
        if exclude_dirs:
            command.extend(["/XD", *exclude_dirs])
        if exclude_files:
            command.extend(["/XF", *exclude_files])
        completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode > 7:
            message = (completed.stderr or completed.stdout).strip() or "Robocopy fehlgeschlagen."
            raise RuntimeError(f"{message} (ExitCode={completed.returncode})")


@contextmanager
def mounted_paths(module_root: Path, staging_dir: Path):
    if os.name != "nt":
        yield module_root, staging_dir
        return
    base_dir = Path(tempfile.gettempdir()) / f"vs{os.getpid()}"
    source_link = base_dir / "m"
    stage_link = base_dir / "s"
    clear_junctions(base_dir, source_link, stage_link)
    base_dir.mkdir(parents=True, exist_ok=True)
    if not (create_junction(source_link, module_root) and create_junction(stage_link, staging_dir)):
        yield module_root, staging_dir
        return
    try:
        yield source_link, stage_link
    finally:
        clear_junctions(base_dir, source_link, stage_link)
        with suppress(OSError):
            base_dir.rmdir()


def clear_junctions(base_dir: Path, source_link: Path, stage_link: Path) -> None:
    if not base_dir.exists():
        return
    for link in (source_link, stage_link):
        subprocess.run(["cmd", "/c", "rmdir", str(link)], check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")


def create_junction(link_path: Path, target_path: Path) -> bool:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(["cmd", "/c", "mklink", "/J", str(link_path), str(target_path)], check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return completed.returncode == 0 and link_path.exists()
