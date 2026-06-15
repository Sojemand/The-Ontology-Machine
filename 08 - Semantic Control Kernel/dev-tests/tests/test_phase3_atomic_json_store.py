from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.paths import StatePaths


def _validator(payload) -> None:
    if payload.get("schema_version") != "example.v1":
        raise ValueError("invalid schema")


def test_atomic_json_writes_valid_payload_and_reads_back(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "example")
    target = paths.safe_path("workflow_runs", "active", "example.json")

    written = store.write_json(target, {"schema_version": "example.v1", "value": 1}, validator=_validator)

    assert written == {"schema_version": "example.v1", "value": 1}
    assert target.read_text(encoding="utf-8").endswith("\n")
    assert store.read_json(target, validator=_validator) == written


def test_atomic_json_rejects_invalid_payload_before_replace(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "example")
    target = paths.safe_path("workflow_runs", "active", "example.json")
    store.write_json(target, {"schema_version": "example.v1", "value": "original"}, validator=_validator)

    with pytest.raises(ValueError):
        store.write_json(target, {"schema_version": "wrong.v1", "value": "bad"}, validator=_validator)

    assert store.read_json(target, validator=_validator)["value"] == "original"


def test_atomic_json_preserves_existing_file_when_temp_write_fails(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "example")
    target = paths.safe_path("workflow_runs", "active", "example.json")
    store.write_json(target, {"schema_version": "example.v1", "value": "original"}, validator=_validator)

    original_write_text = Path.write_text

    def fail_temp_write(self, *args, **kwargs):
        if self.parent == paths.tmp_dir:
            raise OSError("simulated temp write failure")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_temp_write)

    with pytest.raises(Exception):
        store.write_json(target, {"schema_version": "example.v1", "value": "new"}, validator=_validator)

    assert store.read_json(target, validator=_validator)["value"] == "original"


def test_atomic_json_retries_transient_replace_permission_error(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "example")
    target = paths.safe_path("workflow_runs", "active", "example.json")
    original_replace = os.replace
    attempts = 0

    def flaky_replace(src, dst):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError(5, "Access is denied", str(dst))
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)

    written = store.write_json(target, {"schema_version": "example.v1", "value": "new"}, validator=_validator)

    assert attempts == 2
    assert written["value"] == "new"
    assert store.read_json(target, validator=_validator)["value"] == "new"


def test_atomic_json_quarantines_orphan_temp_files_older_than_one_hour(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "example")
    orphan = paths.tmp_dir / "orphan.tmp"
    orphan.write_text("partial", encoding="utf-8")
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    os.utime(orphan, (old.timestamp(), old.timestamp()))

    moved = store.quarantine_orphan_temp_files()

    assert len(moved) == 1
    assert not orphan.exists()
    assert moved[0].is_relative_to(paths.quarantine_partial_writes_dir)
    assert moved[0].with_name(moved[0].name + ".reason.json").exists()
