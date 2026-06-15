"""JSON and timestamp helpers for Corpus Builder boundaries."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_bytes_write(path: Path, data: bytes) -> None:
    def _write(tmp_path: Path) -> None:
        with open(_as_os_path(tmp_path), "wb") as handle:
            handle.write(data)

    atomic_file_write(path, _write)


def atomic_text_write(path: Path, data: str, *, encoding: str = "utf-8", newline: str | None = None) -> None:
    def _write(tmp_path: Path) -> None:
        with open(_as_os_path(tmp_path), "w", encoding=encoding, newline=newline) as handle:
            handle.write(data)

    atomic_file_write(path, _write)


def atomic_json_write(
    path: Path,
    data: dict[str, Any],
    *,
    sort_keys: bool = False,
    trailing_newline: bool = False,
) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=sort_keys)
    if trailing_newline:
        payload += "\n"
    atomic_text_write(path, payload)


def atomic_file_write(path: Path, writer: Callable[[Path], None]) -> None:
    path = Path(path)
    _ensure_parent(path.parent)
    file_handle, tmp_name = tempfile.mkstemp(
        prefix=".",
        suffix=".tmp",
        dir=_as_os_path(path.parent),
    )
    os.close(file_handle)
    tmp_path = Path(tmp_name)
    try:
        writer(tmp_path)
        _fsync_file(tmp_path)
        _replace_file_with_retry(tmp_path, path)
    except BaseException:
        _unlink_missing_ok(tmp_path)
        raise


def _ensure_parent(path: Path) -> None:
    os.makedirs(_as_os_path(path), exist_ok=True)


def _replace_file_with_retry(source: Path, target: Path) -> None:
    for attempt in range(10):
        try:
            os.replace(_as_os_path(source), _as_os_path(target))
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.01 * (attempt + 1))


def _unlink_missing_ok(path: Path) -> None:
    try:
        os.unlink(_as_os_path(path))
    except FileNotFoundError:
        return


def _fsync_file(path: Path) -> None:
    try:
        descriptor = os.open(_as_os_path(path), os.O_RDWR)
    except OSError:
        return
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            return
    finally:
        os.close(descriptor)


def _as_os_path(path: Path) -> str:
    resolved = Path(path).resolve(strict=False)
    text = str(resolved)
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text
