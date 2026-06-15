from __future__ import annotations

import shutil
from pathlib import Path


def materialize_wheelhouse(wheelhouse_dir: str | Path) -> Path:
    target_dir = Path(wheelhouse_dir)
    archive_path = wheelhouse_archive_path(target_dir)
    if target_dir.exists() and any(target_dir.iterdir()):
        return target_dir
    if not archive_path.exists():
        return target_dir
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=False)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(archive_path), str(target_dir.parent))
    return target_dir


def archive_wheelhouse(wheelhouse_dir: str | Path, *, prune: bool = True) -> Path | None:
    source_dir = Path(wheelhouse_dir)
    if not source_dir.exists() or not any(source_dir.iterdir()):
        return None
    archive_path = wheelhouse_archive_path(source_dir)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    shutil.make_archive(str(archive_path.with_suffix("")), "zip", root_dir=str(source_dir.parent), base_dir=source_dir.name)
    if prune:
        shutil.rmtree(source_dir, ignore_errors=False)
    return archive_path


def wheelhouse_archive_path(wheelhouse_dir: str | Path) -> Path:
    source_dir = Path(wheelhouse_dir)
    return source_dir.parent / f"{source_dir.name}.zip"
