from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import ingestion_layer_file.processor.claims_repository as file_claims
from ingestion_layer_vision.processor import Processor, _RUN_LOCK_NAME


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait(timeout=10)
    return int(process.pid)


def _write_stale_lock(output_dir: Path) -> int:
    pid = _dead_pid()
    (output_dir / _RUN_LOCK_NAME).write_text(
        json.dumps({"pid": pid, "created_at": "2026-03-30T00:00:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    return pid


def test_try_claim_output_dir_reclaims_stale_dead_pid_lock(tmp_path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    stale_pid = _write_stale_lock(output_dir)
    proc = SimpleNamespace(_run_lock_path=None)

    claimed = Processor._try_claim_output_dir(proc, output_dir)

    assert claimed == output_dir
    assert proc._run_lock_path == output_dir / _RUN_LOCK_NAME
    payload = json.loads((output_dir / _RUN_LOCK_NAME).read_text(encoding="utf-8"))
    assert payload["pid"] == os.getpid()
    assert payload["pid"] != stale_pid

    Processor._release_output_claim(proc)
    assert not (output_dir / _RUN_LOCK_NAME).exists()


def test_file_profile_run_lock_reclaims_reused_pid_claim(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    lock_path = output_dir / _RUN_LOCK_NAME
    lock_path.write_text(
        json.dumps({"pid": 12345, "created_at": "2026-03-30T00:00:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(file_claims, "_pid_is_running", lambda _pid: True)
    monkeypatch.setattr(file_claims, "_process_started_at", lambda _pid: file_claims.datetime(2026, 3, 30, 0, 1, 0))
    proc = SimpleNamespace(_run_lock_path=None)

    claimed = file_claims.try_claim_output_dir(proc, output_dir)

    assert claimed == output_dir
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    assert payload["pid"] == os.getpid()


def test_file_profile_run_lock_keeps_active_matching_pid_claim(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    lock_path = output_dir / _RUN_LOCK_NAME
    lock_path.write_text(
        json.dumps({"pid": 12345, "created_at": "2026-03-30T00:01:00"}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(file_claims, "_pid_is_running", lambda _pid: True)
    monkeypatch.setattr(file_claims, "_process_started_at", lambda _pid: file_claims.datetime(2026, 3, 30, 0, 0, 59))
    proc = SimpleNamespace(_run_lock_path=None)

    assert file_claims.try_claim_output_dir(proc, output_dir) is None
    assert json.loads(lock_path.read_text(encoding="utf-8"))["pid"] == 12345
