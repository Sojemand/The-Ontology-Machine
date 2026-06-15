"""Local DPAPI-backed OAuth token cache for the Orchestrator."""

from __future__ import annotations

import base64
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..locking import timed_file_lock
from ..state import atomic_text_write
from .oauth_metadata import build_token_bundle
from .oauth_types import OAuthTokenBundle

_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_RETRY_DELAY_SECONDS = 0.01


def token_cache_path(state_dir: Path) -> Path:
    return Path(state_dir) / "oauth_token.enc"


def token_lock_path(state_dir: Path) -> Path:
    return Path(state_dir) / "oauth_token.lock"


def save_token(state_dir: Path, token: OAuthTokenBundle) -> None:
    _ensure_dpapi()
    payload = {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "id_token": token.id_token,
        "token_type": token.token_type,
        "expires_at": token.expires_at,
        "account_id": token.account_id,
        "client_id": token.client_id,
        "session_id": token.session_id,
        "scope": token.scope,
        "token_status_code": token.token_status_code,
    }
    encrypted = _dpapi_encrypt(json.dumps(payload).encode("utf-8"))
    with _token_lock(state_dir):
        atomic_text_write(token_cache_path(state_dir), base64.b64encode(encrypted).decode("ascii"))


def load_token(state_dir: Path) -> OAuthTokenBundle | None:
    if not _dpapi_available():
        return None
    path = token_cache_path(state_dir)
    if not path.exists():
        return None
    try:
        raw = base64.b64decode(path.read_text(encoding="utf-8"))
        payload = json.loads(_dpapi_decrypt(raw).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        return None
    return build_token_bundle(
        access_token=access_token,
        refresh_token=str(payload.get("refresh_token") or ""),
        id_token=str(payload.get("id_token") or ""),
        token_type=str(payload.get("token_type") or "Bearer"),
        scope=str(payload.get("scope") or ""),
        status_code=int(payload.get("token_status_code") or 200),
        fallback_account_id=str(payload.get("account_id") or ""),
        fallback_expires_at=str(payload.get("expires_at") or ""),
        fallback_client_id=str(payload.get("client_id") or ""),
        fallback_session_id=str(payload.get("session_id") or ""),
    )


def delete_token(state_dir: Path) -> bool:
    with _token_lock(state_dir):
        path = token_cache_path(state_dir)
        if not path.exists():
            return False
        path.unlink()
        return True


def has_token(state_dir: Path) -> bool:
    return token_cache_path(state_dir).exists()


def _dpapi_available() -> bool:
    return sys.platform == "win32"


def _ensure_dpapi() -> None:
    if not _dpapi_available():
        raise RuntimeError("OAuth token storage is only available on Windows via DPAPI.")


def _dpapi_encrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    blob_in, buffer_in = _blob_from_bytes(DATA_BLOB, data)
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI CryptProtectData failed")
    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    del buffer_in
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _dpapi_decrypt(data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    blob_in, buffer_in = _blob_from_bytes(DATA_BLOB, data)
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI CryptUnprotectData failed")
    result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    del buffer_in
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return result


def _blob_from_bytes(blob_type: Any, data: bytes):
    import ctypes

    buffer = ctypes.create_string_buffer(data, len(data))
    return blob_type(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


@contextmanager
def _token_lock(state_dir: Path):
    path = token_lock_path(state_dir)
    with timed_file_lock(
        path,
        timeout_seconds=_LOCK_TIMEOUT_SECONDS,
        retry_delay_seconds=_LOCK_RETRY_DELAY_SECONDS,
        timeout_message=f"OAuth token lock could not be acquired: {path}",
    ):
        yield
