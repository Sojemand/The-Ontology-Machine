"""JSON, hashing, timestamp, and serialization helpers for normalizer boundaries."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_ATOMIC_TEMP_PREFIX = ".t."
_ATOMIC_TEMP_SUFFIX = ".tmp"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=_ATOMIC_TEMP_PREFIX,
        suffix=_ATOMIC_TEMP_SUFFIX,
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(file_handle, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            _flush_for_replace(handle)
        _replace_file_with_retry(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def atomic_text_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=_ATOMIC_TEMP_PREFIX,
        suffix=_ATOMIC_TEMP_SUFFIX,
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(file_handle, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            _flush_for_replace(handle)
        _replace_file_with_retry(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{label} ist kein JSON-Objekt: {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root muss ein Objekt sein: {path}")
    return data


def to_json_compatible(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_json_compatible(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_compatible(item) for item in value]
    raise TypeError(f"Nicht JSON-serialisierbarer Wert: {type(value).__name__}")


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _replace_file_with_retry(source: Path, target: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.01 * (attempt + 1))


def _flush_for_replace(handle) -> None:
    handle.flush()
    os.fsync(handle.fileno())
