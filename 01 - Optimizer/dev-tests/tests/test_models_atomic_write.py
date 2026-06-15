from __future__ import annotations

import json
import os
import tempfile
import threading

import pytest

from ingestion_layer_vision.models import atomic_json_write
import ingestion_layer_vision.models.repository as repository


class TestAtomicJsonWriteBasic:
    def test_write_overwrite_and_create_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "test.json"
        atomic_json_write(path, {"key": "value", "number": 42})
        assert json.loads(path.read_text(encoding="utf-8")) == {"key": "value", "number": 42}
        atomic_json_write(path, {"new": True})
        assert json.loads(path.read_text(encoding="utf-8")) == {"new": True}

    def test_concurrent_writes_to_same_target_do_not_fail(self, tmp_path):
        path = tmp_path / "shared.json"
        errors = []
        barrier = threading.Barrier(6)

        def worker(worker_id: int) -> None:
            try:
                barrier.wait()
                for index in range(25):
                    atomic_json_write(path, {"worker": worker_id, "index": index})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(worker_id,)) for worker_id in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert errors == []
        assert set(json.loads(path.read_text(encoding="utf-8"))) == {"worker", "index"}


class TestAtomicJsonWriteRetries:
    def test_retries_transient_permission_errors(self, tmp_path, monkeypatch):
        path = tmp_path / "state.json"
        payload = {"status": "ok"}
        real_replace = os.replace
        attempts = []

        def flaky_replace(src, dst):
            attempts.append((src, dst))
            if len(attempts) < 3:
                raise PermissionError("locked")
            return real_replace(src, dst)

        monkeypatch.setattr("ingestion_layer_vision.models.os.replace", flaky_replace)
        atomic_json_write(path, payload)
        assert len(attempts) == 3
        assert json.loads(path.read_text(encoding="utf-8")) == payload

    def test_removes_temp_file_when_replace_keeps_failing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ingestion_layer_vision.models.os.replace", lambda src, dst: (_ for _ in ()).throw(PermissionError("locked")))
        with pytest.raises(PermissionError, match="locked"):
            atomic_json_write(tmp_path / "state.json", {"status": "broken"})
        assert list(tmp_path.glob("*.tmp")) == []

    def test_uses_short_temp_prefix_for_long_names(self, tmp_path, monkeypatch):
        path = tmp_path / ("x" * 120 + ".raw.json")
        captured: dict[str, str] = {}
        original_mkstemp = tempfile.mkstemp

        def _mkstemp(*args, **kwargs):
            captured["prefix"] = kwargs["prefix"]
            return original_mkstemp(*args, **kwargs)

        monkeypatch.setattr(repository.tempfile, "mkstemp", _mkstemp)
        atomic_json_write(path, {"ok": True})

        assert path.exists()
        assert len(captured["prefix"]) <= 35
        assert "x" * 25 not in captured["prefix"]
