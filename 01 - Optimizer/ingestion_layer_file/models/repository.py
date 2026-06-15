"""Repository layer for atomic writes and persisted models state."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

_ATOMIC_WRITE_LOCKS: dict[str, threading.Lock] = {}
_ATOMIC_WRITE_LOCKS_GUARD = threading.Lock()
_TEMP_STEM_RE = re.compile(r"[^A-Za-z0-9._-]+")


def atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def atomic_text_write(path: Path, text: str) -> None:
    _atomic_write(path, text)


def atomic_bytes_write(path: Path, data: bytes) -> None:
    _atomic_write(path, data)


def atomic_file_copy(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with _atomic_write_lock(target_path):
        tmp_path: Path | None = None
        fd = -1
        try:
            fd, tmp_name = tempfile.mkstemp(prefix=_temp_prefix(target_path), suffix=".tmp", dir=str(target_path.parent))
            tmp_path = Path(tmp_name)
            with source_path.open("rb") as source, os.fdopen(fd, "wb") as target:
                fd = -1
                shutil.copyfileobj(source, target, length=1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            _replace_with_retry(tmp_path, target_path)
        except Exception:
            if fd != -1:
                os.close(fd)
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise


def _atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _atomic_write_lock(path):
        tmp_path: Path | None = None
        fd = -1
        try:
            fd, tmp_name = tempfile.mkstemp(prefix=_temp_prefix(path), suffix=".tmp", dir=str(path.parent))
            tmp_path = Path(tmp_name)
            if isinstance(content, bytes):
                handle = os.fdopen(fd, "wb")
            else:
                handle = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
            with handle:
                fd = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            _replace_with_retry(tmp_path, path)
        except Exception:
            if fd != -1:
                os.close(fd)
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise


def _atomic_write_lock(path: Path) -> threading.Lock:
    key = str(path)
    with _ATOMIC_WRITE_LOCKS_GUARD:
        return _ATOMIC_WRITE_LOCKS.setdefault(key, threading.Lock())


def _temp_prefix(path: Path) -> str:
    safe_stem = _TEMP_STEM_RE.sub("_", path.stem).strip("._") or "document"
    digest = hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:8]
    return f".{safe_stem[:24]}.{digest}."


def _replace_with_retry(src: Path, dst: Path, attempts: int = 8) -> None:
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(0.01 * (attempt + 1))
    if last_error is not None:
        raise last_error
