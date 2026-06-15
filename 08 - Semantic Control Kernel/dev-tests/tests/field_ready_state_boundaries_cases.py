from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from semantic_control_kernel.repository.errors import StateFileReadUnavailableError
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.hard_cap import (
    FS_LOCK_FILE_HARD_CAP,
    RAW_ADAPTER_CALL_TOTAL_BYTES_HARD_CAP,
    KernelStateHardCapService,
)
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.types.merge import MergeWorkflowBlocker
from semantic_control_kernel.workflows.merge.source_selection_builder import build_database_merge_selection

from phase4_adapter_invocation_support import _invoke


def _merge_sources(tmp_path: Path) -> list[dict[str, str]]:
    return [
        {
            "source_database_path": str(tmp_path / "a" / "Corpus" / "corpus.db"),
            "source_artifact_root": str(tmp_path / "a"),
            "source_state": "empty",
            "source_semantic_release_id": "rel",
            "source_semantic_release_version": "1",
            "source_release_fingerprint": "sha256:a",
            "source_artifact_tree_fingerprint": "sha256:aa",
        },
        {
            "source_database_path": str(tmp_path / "b" / "Corpus" / "corpus.db"),
            "source_artifact_root": str(tmp_path / "b"),
            "source_state": "empty",
            "source_semantic_release_id": "rel",
            "source_semantic_release_version": "1",
            "source_release_fingerprint": "sha256:b",
            "source_artifact_tree_fingerprint": "sha256:bb",
        },
    ]


def test_transient_read_error_does_not_quarantine_valid_state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = AtomicJsonStore(paths, "field_ready")
    target = paths.safe_path("workflow_runs", "active", "valid.json")
    store.write_json(target, {"schema_version": "field_ready.v1", "value": 1})

    def fail_read(_path: Path) -> str:
        raise PermissionError(5, "Access is denied", str(target))

    monkeypatch.setattr("semantic_control_kernel.repository.atomic_json_store._read_text_for_io", fail_read)

    with pytest.raises(StateFileReadUnavailableError):
        store.read_json(target)

    assert target.exists()
    assert list(paths.quarantine_corrupt_dir.rglob("valid.json")) == []


def test_prune_all_caps_fs_lock_files(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    for index in range(FS_LOCK_FILE_HARD_CAP + 12):
        lock_file = paths.fs_locks_dir / f"{index:04d}.lock"
        lock_file.write_bytes(b"\0")
        old_timestamp = time.time() - (FS_LOCK_FILE_HARD_CAP + 12 - index)
        os.utime(lock_file, (old_timestamp, old_timestamp))

    KernelStateHardCapService(paths).prune_all()

    assert len(list(paths.fs_locks_dir.glob("*.lock"))) == FS_LOCK_FILE_HARD_CAP


def test_terminal_workflow_transition_recovers_after_history_write_delete_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    store = WorkflowRunStore(paths)
    run = store.create_run("manual_pipeline_run", {"target_hash": "terminal_recovery"}, "field_ready")
    active_path = paths.workflow_runs_active_dir / f"{run.workflow_run_id}.json"
    history_path = paths.workflow_runs_history_dir / f"{run.workflow_run_id}.json"
    original_delete = store._json.delete_json

    def fail_delete(_path: Path) -> None:
        raise PermissionError("simulated active delete failure")

    monkeypatch.setattr(store._json, "delete_json", fail_delete)
    with pytest.raises(PermissionError):
        store.mark_run_completed(run.workflow_run_id, "opr_terminal")

    assert active_path.exists()
    assert history_path.exists()

    monkeypatch.setattr(store._json, "delete_json", original_delete)
    recovered = store.mark_run_completed(run.workflow_run_id, "opr_terminal")

    assert recovered.status == "completed"
    assert not active_path.exists()
    assert history_path.exists()


def test_raw_adapter_call_pruning_obeys_total_byte_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    monkeypatch.setattr("semantic_control_kernel.repository.hard_cap.RAW_ADAPTER_CALL_TOTAL_BYTES_HARD_CAP", 300)
    monkeypatch.setattr("semantic_control_kernel.repository.hard_cap.RAW_ADAPTER_CALL_DIR_BYTES_HARD_CAP", 10_000)
    for index in range(4):
        call_dir = paths.adapter_calls_dir / f"adc_size_{index:04d}"
        call_dir.mkdir(parents=True, exist_ok=True)
        (call_dir / "owner_response.raw.json").write_text("x" * 150, encoding="utf-8")

    KernelStateHardCapService(paths).prune_raw_adapter_calls()

    total = sum(path.stat().st_size for path in paths.adapter_calls_dir.rglob("*") if path.is_file())
    assert total <= 300
    assert total <= RAW_ADAPTER_CALL_TOTAL_BYTES_HARD_CAP


def test_owner_timeout_terminates_child_process_tree(tmp_path: Path) -> None:
    marker = tmp_path / "late_child_marker.txt"

    result, _call_dir, _payload = _invoke(
        tmp_path,
        "spawn_child_timeout",
        timeout_seconds=0.2,
        extra_payload={"child_marker_path": str(marker), "child_sleep_seconds": 0.6, "sleep_seconds": 10},
    )
    time.sleep(1.0)

    assert result.status == "timeout"
    assert not marker.exists()


def test_merge_selection_blocks_target_database_outside_artifact_corpus(tmp_path: Path) -> None:
    selection = build_database_merge_selection(
        selected_sources=_merge_sources(tmp_path),
        target_artifact_root=tmp_path / "target",
        target_database_path=tmp_path / "elsewhere" / "corpus.db",
        selected_by_interaction_id="irq_target_escape",
    )

    assert isinstance(selection, MergeWorkflowBlocker)
    assert selection.blocker_code == "target_path_escape"


def test_merge_selection_accepts_relative_database_name_inside_corpus(tmp_path: Path) -> None:
    selection = build_database_merge_selection(
        selected_sources=_merge_sources(tmp_path),
        target_artifact_root=tmp_path / "target",
        target_database_path="custom.db",
        selected_by_interaction_id="irq_target_relative",
    )

    assert not isinstance(selection, MergeWorkflowBlocker)
    assert Path(selection.to_dict()["target_database_path"]) == (tmp_path / "target" / "Corpus" / "custom.db").resolve(strict=False)
