"""Atomic-write edge tests for ingestion_layer_vision.models."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from ingestion_layer_vision.models import _ATOMIC_WRITE_LOCKS, _ATOMIC_WRITE_LOCKS_GUARD, _atomic_write_lock, atomic_json_write


class TestAtomicWriteRetry:
    def test_atomic_write_retry_on_permission_error(self, tmp_path, monkeypatch):
        target = tmp_path / "retry_ok.json"
        payload = {"status": "written"}
        real_replace = os.replace
        counter = {"n": 0}

        def flaky_replace(src, dst):
            counter["n"] += 1
            if counter["n"] <= 3:
                raise PermissionError("file in use")
            return real_replace(src, dst)

        monkeypatch.setattr("ingestion_layer_vision.models.os.replace", flaky_replace)
        monkeypatch.setattr("ingestion_layer_vision.models.time.sleep", lambda _: None)
        atomic_json_write(target, payload)
        assert counter["n"] == 4
        assert json.loads(target.read_text(encoding="utf-8")) == payload

    def test_atomic_write_all_retries_exhausted(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ingestion_layer_vision.models.os.replace", lambda src, dst: (_ for _ in ()).throw(PermissionError("locked")))
        monkeypatch.setattr("ingestion_layer_vision.models.time.sleep", lambda _: None)
        with pytest.raises(PermissionError, match="locked"):
            atomic_json_write(tmp_path / "never.json", {"fail": True})

    def test_atomic_write_temp_cleaned_on_json_dump_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ingestion_layer_vision.models.json.dump", lambda *a, **kw: (_ for _ in ()).throw(TypeError("not serializable")))
        with pytest.raises(TypeError, match="not serializable"):
            atomic_json_write(tmp_path / "dump_fail.json", {"bad": object()})
        assert list(tmp_path.glob(".dump_fail.json.*.tmp")) == []


class TestAtomicWriteConcurrency:
    def test_atomic_write_concurrent_same_path(self, tmp_path):
        target = tmp_path / "shared.json"
        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        def writer(data: dict) -> None:
            try:
                barrier.wait()
                for _ in range(20):
                    atomic_json_write(target, data)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=({"writer": idx},)) for idx in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert errors == []
        assert json.loads(target.read_text(encoding="utf-8")) in ({"writer": 1}, {"writer": 2})


class TestAtomicWriteBookkeeping:
    def test_atomic_write_lock_same_path_same_object(self):
        key = Path("test/file.json")
        lock_a = _atomic_write_lock(key)
        lock_b = _atomic_write_lock(key)
        assert lock_a is lock_b
        with _ATOMIC_WRITE_LOCKS_GUARD:
            _ATOMIC_WRITE_LOCKS.pop(str(key), None)

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "deep.json"
        atomic_json_write(target, {"deep": True})
        assert json.loads(target.read_text(encoding="utf-8")) == {"deep": True}
