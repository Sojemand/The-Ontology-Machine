"""Local DPAPI-backed keystore for orchestrator credential secrets."""

from __future__ import annotations

import base64
import json
import logging
import sys
from contextlib import contextmanager
from pathlib import Path

from ..locking import timed_file_lock
from ..models import ProviderEndpointSettings
from ..state.adapter import atomic_json_write
from .policy import secret_name_for_provider_target, secret_name_for_target, uses_legacy_secret_for_provider
from .validation import ensure_target

logger = logging.getLogger(__name__)

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_RETRY_DELAY_SECONDS = 0.01
_dpapi_available = lambda: sys.platform == "win32"


def _store_path(state_dir: Path) -> Path:
    return Path(state_dir) / "keystore.enc"


def _lock_path(state_dir: Path) -> Path:
    return Path(state_dir) / "keystore.lock"


def _dpapi_encrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI CryptProtectData failed")
    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _dpapi_decrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI CryptUnprotectData failed")
    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _load_store(state_dir: Path) -> dict[str, str]:
    path = _store_path(state_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Broken Orchestrator keystore is treated as empty: %s", exc)
        return {}
    if not isinstance(payload, dict):
        logger.warning("Orchestrator keystore does not have JSON object format: %s", path)
        return {}
    return {str(key): str(value) for key, value in payload.items() if isinstance(key, str) and isinstance(value, str)}


def _save_store(state_dir: Path, store: dict[str, str]) -> None:
    atomic_json_write(_store_path(state_dir), store)


@contextmanager
def _store_lock(state_dir: Path):
    path = _lock_path(state_dir)
    with timed_file_lock(
        path,
        timeout_seconds=_LOCK_TIMEOUT_SECONDS,
        retry_delay_seconds=_LOCK_RETRY_DELAY_SECONDS,
        timeout_message=f"Orchestrator keystore lock could not be acquired: {path}",
    ):
        yield


def save_api_key(
    state_dir: Path, target: str, value: str, *, provider_settings: ProviderEndpointSettings | None = None
) -> None:
    ensure_target(target)
    if not value.strip():
        raise ValueError("Empty API key cannot be saved")
    if not _dpapi_available():
        raise RuntimeError("Secure key storage is only available on Windows via DPAPI")
    with _store_lock(state_dir):
        store = _load_store(state_dir)
        encrypted = _dpapi_encrypt(value.encode("utf-8"))
        secret_name = _primary_secret_name(target, provider_settings=provider_settings)
        store[secret_name] = base64.b64encode(encrypted).decode("ascii")
        _save_store(state_dir, store)


def load_api_key(
    state_dir: Path,
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> str | None:
    ensure_target(target)
    if not _dpapi_available():
        return None
    store = _load_store(state_dir)
    for secret_name in _candidate_secret_names(target, provider_settings=provider_settings):
        encoded = store.get(secret_name)
        if not encoded:
            continue
        try:
            return _dpapi_decrypt(base64.b64decode(encoded)).decode("utf-8")
        except Exception as exc:
            logger.warning("Orchestrator keystore could not load key for %s: %s", target, exc)
            return None
    return None


def delete_api_key(
    state_dir: Path,
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> bool:
    ensure_target(target)
    with _store_lock(state_dir):
        store = _load_store(state_dir)
        removed = False
        for secret_name in _candidate_secret_names(target, provider_settings=provider_settings):
            removed = store.pop(secret_name, None) is not None or removed
        if removed:
            _save_store(state_dir, store)
        return removed


def has_api_key(
    state_dir: Path,
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None = None,
) -> bool:
    ensure_target(target)
    store = _load_store(state_dir)
    return any(secret_name in store for secret_name in _candidate_secret_names(target, provider_settings=provider_settings))


def _primary_secret_name(target: str, *, provider_settings: ProviderEndpointSettings | None) -> str:
    if provider_settings is None:
        return secret_name_for_target(target)
    return secret_name_for_provider_target(target, provider_settings)


def _candidate_secret_names(
    target: str,
    *,
    provider_settings: ProviderEndpointSettings | None,
) -> tuple[str, ...]:
    names: list[str] = []
    if provider_settings is not None:
        names.append(secret_name_for_provider_target(target, provider_settings))
        if uses_legacy_secret_for_provider(target, provider_settings):
            names.append(secret_name_for_target(target))
    else:
        names.append(secret_name_for_target(target))
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return tuple(ordered)
