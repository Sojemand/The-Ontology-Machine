"""Filesystem state transitions for published page-image assets."""
from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path

_ASSET_DIR_LOCKS: dict[str, threading.Lock] = {}
_ASSET_DIR_LOCKS_GUARD = threading.Lock()
_PUBLISH_RETRY_ATTEMPTS = 8
_STAGE_DIR_PREFIX = ".stage."


def create_stage_dir(dest_dir: Path) -> Path:
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(
            prefix=_STAGE_DIR_PREFIX,
            suffix=".tmp",
            dir=str(dest_dir.parent),
        )
    )


def publish_stage_dir(stage_dir: Path, dest_dir: Path, paths: list[str]) -> list[str]:
    stage_root = _resolve_path(stage_dir)
    relatives: list[Path] = []
    for raw_path in paths:
        candidate = _resolve_path(Path(raw_path))
        try:
            relative = candidate.relative_to(stage_root)
        except ValueError as exc:
            raise RuntimeError(f"Renderer lieferte einen ungueltigen Asset-Pfad: {raw_path}") from exc
        staged_file = stage_dir / relative
        if not staged_file.is_file():
            raise RuntimeError(f"Vision-Asset fehlt im Staging-Verzeichnis: {staged_file}")
        relatives.append(relative)

    with _asset_dir_lock(dest_dir):
        _replace_dir_with_retry(stage_dir, dest_dir)
    return [str((dest_dir / relative).resolve()) for relative in relatives]


def cleanup_stage_dir(stage_dir: Path) -> None:
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)


def clear_existing_asset_dir(dest_dir: Path) -> None:
    with _asset_dir_lock(dest_dir):
        for attempt in range(_PUBLISH_RETRY_ATTEMPTS):
            try:
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                return
            except PermissionError:
                if attempt == _PUBLISH_RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(0.01 * (attempt + 1))


def _replace_dir_with_retry(stage_dir: Path, dest_dir: Path) -> None:
    last_error: OSError | None = None
    for attempt in range(_PUBLISH_RETRY_ATTEMPTS):
        try:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            stage_dir.rename(dest_dir)
            return
        except (FileExistsError, PermissionError) as exc:
            last_error = exc
            if attempt == _PUBLISH_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(0.01 * (attempt + 1))
    if last_error is not None:  # pragma: no cover
        raise last_error


def _resolve_path(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def _asset_dir_lock(path: Path) -> threading.Lock:
    key = str(_resolve_path(path))
    with _ASSET_DIR_LOCKS_GUARD:
        return _ASSET_DIR_LOCKS.setdefault(key, threading.Lock())
