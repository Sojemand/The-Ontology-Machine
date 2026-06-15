from __future__ import annotations

import os
from datetime import datetime, timedelta

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

_LOCK_START_TOLERANCE_SECONDS = 5.0

if os.name == "nt":
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class _FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _KERNEL32.OpenProcess.restype = wintypes.HANDLE
    _KERNEL32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_FILETIME),
        ctypes.POINTER(_FILETIME),
        ctypes.POINTER(_FILETIME),
        ctypes.POINTER(_FILETIME),
    ]
    _KERNEL32.GetProcessTimes.restype = wintypes.BOOL
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = wintypes.BOOL


def pid_claim_is_active(pid: int, created_at: object) -> bool:
    if not _pid_is_running(pid):
        return False
    lock_created_at = _parse_lock_created_at(created_at)
    if lock_created_at is None:
        return True
    started_at = _process_started_at(pid)
    if started_at is None:
        return True
    return started_at <= lock_created_at + timedelta(seconds=_LOCK_START_TOLERANCE_SECONDS)


def _pid_is_running(pid: int) -> bool:
    if os.name == "nt":
        handle = _KERNEL32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            _KERNEL32.CloseHandle(handle)
            return True
        return ctypes.get_last_error() not in {87}
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        return getattr(exc, "winerror", None) != 87
    return True


def _parse_lock_created_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _process_started_at(pid: int) -> datetime | None:
    if os.name != "nt":
        return None
    handle = _KERNEL32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        created = _FILETIME()
        exited = _FILETIME()
        kernel = _FILETIME()
        user = _FILETIME()
        if not _KERNEL32.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        return _filetime_to_datetime(created)
    finally:
        _KERNEL32.CloseHandle(handle)


def _filetime_to_datetime(filetime: _FILETIME) -> datetime:
    raw_value = (filetime.dwHighDateTime << 32) | filetime.dwLowDateTime
    timestamp = (raw_value - 116444736000000000) / 10000000
    return datetime.fromtimestamp(timestamp)
