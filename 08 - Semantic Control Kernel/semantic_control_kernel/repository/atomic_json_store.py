from __future__ import annotations

import json
import os
import shutil
import time
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from semantic_control_kernel.repository.atomic_json_io import (
    _exists_for_io,
    _open_for_io,
    _read_text_for_io,
    _temp_path_for,
    _unlink_for_io,
    _replace_with_retry,
    _write_text_for_io,
    atomic_write_text,
    ensure_directory,
    stable_json_dumps,
)
from semantic_control_kernel.repository.errors import (
    AtomicWriteError,
    DuplicateStateObjectError,
    StateCorruptionError,
    StateFileLockUnavailableError,
    StateFileReadUnavailableError,
    StateReadAfterWriteError,
)
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id, utc_compact_timestamp
from semantic_control_kernel.repository.paths import StatePaths, path_hash, utc_iso

JsonValidator = Callable[[Mapping[str, Any]], None]
STATE_FILE_LOCK_TIMEOUT_SECONDS = 10.0
STATE_FILE_LOCK_RETRY_SECONDS = 0.05


class AtomicJsonStore:
    def __init__(self, paths: StatePaths, store_name: str) -> None:
        self.paths = paths
        self.store_name = store_name
        self.paths.ensure_layout()

    def write_json(
        self,
        final_path: str | os.PathLike[str],
        payload: Mapping[str, Any],
        *,
        immutable: bool = False,
        validator: JsonValidator | None = None,
        sync_to_disk: bool = True,
        read_back: bool = True,
        file_lock: bool = True,
    ) -> dict[str, Any]:
        final = self.paths.require_under_state_root(final_path)
        ensure_directory(final.parent)
        copied = deepcopy(dict(payload))
        self._validate(copied, validator)
        serialized = stable_json_dumps(copied)
        temp_path = _temp_path_for(final, self.paths.tmp_dir)
        try:
            with self._lock_for(final) if file_lock else nullcontext():
                if immutable and _exists_for_io(final):
                    raise DuplicateStateObjectError(f"State object already exists: {final}")
                _write_text_for_io(temp_path, serialized)
                if sync_to_disk:
                    with _open_for_io(temp_path, "r+b") as handle:
                        handle.flush()
                        os.fsync(handle.fileno())
                _replace_with_retry(temp_path, final)
                return self._read_back_payload(final, copied, validator, read_back)
        except DuplicateStateObjectError:
            if _exists_for_io(temp_path):
                _unlink_for_io(temp_path)
            raise
        except Exception as exc:
            if _exists_for_io(temp_path):
                _unlink_for_io(temp_path)
            if isinstance(exc, (StateReadAfterWriteError, StateFileLockUnavailableError, AtomicWriteError)):
                raise
            raise AtomicWriteError(str(exc)) from exc

    def read_json(self, final_path: str | os.PathLike[str], *, validator: JsonValidator | None = None, quarantine_on_error: bool = True) -> dict[str, Any]:
        final = self.paths.require_under_state_root(final_path)
        try:
            text = _read_text_for_io(final)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise StateFileReadUnavailableError(f"State file is temporarily unreadable: {final}: {exc}") from exc
        try:
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise StateCorruptionError(f"State file must contain a JSON object: {final}")
            self._validate(payload, validator)
            return payload
        except (json.JSONDecodeError, StateCorruptionError, TypeError, ValueError, KeyError) as exc:
            if not quarantine_on_error:
                raise
            quarantined = self._quarantine_file(final, "corrupt", str(exc), exc)
            raise StateCorruptionError(f"Corrupt state file quarantined: {quarantined}") from exc

    def delete_json(self, final_path: str | os.PathLike[str]) -> None:
        final = self.paths.require_under_state_root(final_path)
        with self._lock_for(final):
            if _exists_for_io(final):
                _unlink_for_io(final)

    def quarantine_orphan_temp_files(self, *, older_than_seconds: int = 3600, now_utc: datetime | None = None) -> list[Path]:
        now = now_utc or datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=older_than_seconds)
        moved: list[Path] = []
        for temp_file in self.paths.tmp_dir.glob("*"):
            if temp_file.is_file() and datetime.fromtimestamp(temp_file.stat().st_mtime, timezone.utc) <= cutoff:
                moved.append(self._quarantine_file(temp_file, "partial_writes", f"orphan temp file older than {older_than_seconds} seconds", None))
        return moved

    def _read_back_payload(self, final: Path, copied: dict[str, Any], validator: JsonValidator | None, read_back: bool) -> dict[str, Any]:
        if not read_back:
            return copied
        try:
            read_payload = self.read_json(final, validator=validator, quarantine_on_error=False)
        except Exception as exc:  # pragma: no cover - defensive conversion
            raise StateReadAfterWriteError(f"Read-after-write validation failed for {final}") from exc
        if read_payload != copied:
            raise StateReadAfterWriteError(f"Read-after-write payload mismatch for {final}")
        return read_payload

    def _validate(self, payload: Mapping[str, Any], validator: JsonValidator | None) -> None:
        json.dumps(payload)
        if validator is not None:
            validator(payload)

    @contextmanager
    def _lock_for(self, final_path: Path) -> Iterator[None]:
        self.paths.fs_locks_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.paths.fs_locks_dir / f"{path_hash(final_path)}.lock"
        lock_path.touch(exist_ok=True)
        with lock_path.open("r+b") as handle:
            yield from _locked_handle(handle)

    def _quarantine_file(self, source: Path, category: str, reason: str, exc: BaseException | None) -> Path:
        quarantine_dir = self.paths.quarantine_corrupt_dir / self.store_name if category == "corrupt" else self.paths.quarantine_partial_writes_dir
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantined = quarantine_dir / f"{utc_compact_timestamp()}_{source.name}"
        while quarantined.exists():
            quarantined = quarantine_dir / f"{utc_compact_timestamp()}_{path_hash(quarantined)}_{source.name}"
        if source.exists():
            shutil.move(str(source), str(quarantined))
        self._write_quarantine_reason(quarantined, source, reason, exc)
        KernelStateHardCapService(self.paths).prune_quarantine_dir(quarantine_dir)
        return quarantined

    def _write_quarantine_reason(self, quarantined: Path, source: Path, reason: str, exc: BaseException | None) -> None:
        reason_payload = {
            "created_at": utc_iso(),
            "exception_class": type(exc).__name__ if exc is not None else "None",
            "original_path": self.paths.relative_to_state_root(source),
            "quarantine_id": generate_id("recovery_event_id"),
            "quarantined_path": self.paths.relative_to_state_root(quarantined),
            "reason": reason,
            "schema_version": "repository.quarantine_reason.v1",
        }
        atomic_write_text(quarantined.with_name(quarantined.name + ".reason.json"), stable_json_dumps(reason_payload), temp_dir=self.paths.tmp_dir)


def _locked_handle(handle) -> Iterator[None]:
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            handle.write(b"\0")
            handle.flush()
            handle.seek(0)
            _wait_for_windows_lock(handle, msvcrt)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return
        try:
            import fcntl
        except ImportError as exc:  # pragma: no cover - platform guard
            raise StateFileLockUnavailableError("fcntl is not available on this host.") from exc
        _wait_for_posix_lock(handle, fcntl)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except StateFileLockUnavailableError:
        raise


def _wait_for_windows_lock(handle, msvcrt) -> None:
    deadline = time.monotonic() + STATE_FILE_LOCK_TIMEOUT_SECONDS
    while True:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if time.monotonic() >= deadline:
                raise StateFileLockUnavailableError(
                    f"Timed out waiting for state file lock after {STATE_FILE_LOCK_TIMEOUT_SECONDS:.1f}s."
                ) from exc
            time.sleep(STATE_FILE_LOCK_RETRY_SECONDS)


def _wait_for_posix_lock(handle, fcntl) -> None:
    deadline = time.monotonic() + STATE_FILE_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError as exc:
            if time.monotonic() >= deadline:
                raise StateFileLockUnavailableError(
                    f"Timed out waiting for state file lock after {STATE_FILE_LOCK_TIMEOUT_SECONDS:.1f}s."
                ) from exc
            time.sleep(STATE_FILE_LOCK_RETRY_SECONDS)
