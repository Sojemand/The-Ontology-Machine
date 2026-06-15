from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

_ATOMIC_REPLACE_ATTEMPTS = 5
_ATOMIC_REPLACE_RETRY_SECONDS = 0.05
_WINDOWS_TRANSIENT_REPLACE_ERRORS = {5, 32}
_WINDOWS_EXTENDED_PATH_THRESHOLD = 240


def stable_json_dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def atomic_write_text(
    final_path: str | os.PathLike[str],
    text: str,
    *,
    temp_dir: str | os.PathLike[str] | None = None,
    sync_to_disk: bool = True,
) -> None:
    final = Path(final_path)
    ensure_directory(final.parent)
    temp_root = Path(temp_dir) if temp_dir is not None else final.parent
    ensure_directory(temp_root)
    temp_path = _temp_path_for(final, temp_root)
    try:
        _write_text_for_io(temp_path, text)
        if sync_to_disk:
            with _open_for_io(temp_path, "r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())
        _replace_with_retry(temp_path, final)
    except Exception:
        if _exists_for_io(temp_path):
            _unlink_for_io(temp_path)
        raise


def atomic_write_json(
    final_path: str | os.PathLike[str],
    payload: Any,
    *,
    temp_dir: str | os.PathLike[str] | None = None,
    sort_keys: bool = True,
    ensure_ascii: bool = True,
    sync_to_disk: bool = True,
) -> None:
    atomic_write_text(
        final_path,
        json.dumps(payload, indent=2, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n",
        temp_dir=temp_dir,
        sync_to_disk=sync_to_disk,
    )


def receipt_payload_hash(payload: Mapping[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()


def ensure_directory(path: str | os.PathLike[str]) -> None:
    _path_for_io(Path(path)).mkdir(parents=True, exist_ok=True)


def _is_transient_replace_error(exc: OSError) -> bool:
    winerror = getattr(exc, "winerror", None)
    if isinstance(winerror, int):
        return winerror in _WINDOWS_TRANSIENT_REPLACE_ERRORS
    return isinstance(exc, PermissionError)


def _replace_with_retry(temp_path: Path, final_path: Path) -> None:
    for attempt in range(_ATOMIC_REPLACE_ATTEMPTS):
        try:
            os.replace(_path_for_io(temp_path), _path_for_io(final_path))
            return
        except PermissionError as exc:
            if attempt == _ATOMIC_REPLACE_ATTEMPTS - 1 or not _is_transient_replace_error(exc):
                raise
            time.sleep(_ATOMIC_REPLACE_RETRY_SECONDS)
        except OSError as exc:
            if attempt == _ATOMIC_REPLACE_ATTEMPTS - 1 or not _is_transient_replace_error(exc):
                raise
            time.sleep(_ATOMIC_REPLACE_RETRY_SECONDS)


def _temp_path_for(final_path: Path, temp_dir: Path) -> Path:
    for _ in range(10):
        candidate = temp_dir / f".t{uuid4().hex[:12]}.tmp"
        if not _exists_for_io(candidate):
            return candidate
    return temp_dir / f".t{uuid4().hex}.tmp"


def _path_for_io(path: Path) -> Path:
    if os.name != "nt":
        return path
    text = str(path)
    if len(text) < _WINDOWS_EXTENDED_PATH_THRESHOLD:
        return path
    if text.startswith("\\\\?\\") or not path.is_absolute():
        return path
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text.lstrip("\\"))
    return Path("\\\\?\\" + text)


def _write_text_for_io(path: Path, text: str) -> None:
    _path_for_io(path).write_text(text, encoding="utf-8")


def _read_text_for_io(path: Path) -> str:
    return _path_for_io(path).read_text(encoding="utf-8")


def _open_for_io(path: Path, mode: str):
    return _path_for_io(path).open(mode)


def _exists_for_io(path: Path) -> bool:
    return _path_for_io(path).exists()


def _unlink_for_io(path: Path) -> None:
    _path_for_io(path).unlink()
