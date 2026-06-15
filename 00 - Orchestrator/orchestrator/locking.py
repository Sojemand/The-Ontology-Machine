"""Minimal cross-platform file locking for orchestrator mutations."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import time

if os.name == "nt":  # pragma: no cover - exercised on Windows
    import msvcrt
else:  # pragma: no cover - exercised on POSIX
    import fcntl


class FileLockBusyError(RuntimeError):
    """Raised when a non-blocking file lock cannot be acquired."""


class FileLock:
    """Non-blocking exclusive lock backed by a lock file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._handle = None

    def acquire(self) -> None:
        if self._handle is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("a+b")
        try:
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            self._lock_handle(handle)
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n".encode("utf-8"))
            handle.flush()
            self._handle = handle
        except Exception:
            try:
                handle.close()
            except Exception:
                pass
            raise

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            self._unlock_handle(self._handle)
        finally:
            try:
                self._handle.close()
            finally:
                self._handle = None

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    @staticmethod
    def _lock_handle(handle) -> None:
        try:
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise FileLockBusyError from exc

    @staticmethod
    def _unlock_handle(handle) -> None:
        try:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            return


@contextmanager
def timed_file_lock(
    path: Path,
    *,
    timeout_seconds: float,
    retry_delay_seconds: float,
    timeout_message: str,
):
    """Acquire an OS-backed lock with bounded retry.

    Existing lock files are harmless: ownership is the OS lock, not file presence.
    """

    lock = FileLock(path)
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            lock.acquire()
            break
        except FileLockBusyError:
            if time.monotonic() >= deadline:
                raise TimeoutError(timeout_message) from None
            time.sleep(retry_delay_seconds)
    try:
        yield
    finally:
        lock.release()
