from __future__ import annotations

import json
import logging

import pytest

import orchestrator.state.adapter as state_adapter
import orchestrator.state as state_module
from orchestrator.locking import FileLock, FileLockBusyError
from orchestrator.state import atomic_json_write, load_pipeline_state, load_ui_state


def test_load_ui_state_parses_string_booleans_and_invalid_mode(tmp_path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text(
        json.dumps(
            {
                "input_folder": "input",
                "artifact_folder": "artifacts",
                "corpus_output_folder": "corpus",
                "mode": "unsupported",
            }
        ),
        encoding="utf-8",
    )

    loaded = load_ui_state(path)

    assert loaded.mode == "batch"
    assert loaded.artifact_folder == "artifacts"


def test_load_ui_state_ignores_legacy_review_switch_field(tmp_path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text(
        json.dumps(
            {
                "input_folder": "input",
                "artifact_folder": "artifacts",
                "corpus_output_folder": "corpus",
                "mode": "single",
                "review_to_needs_review": True,
            }
        ),
        encoding="utf-8",
    )

    loaded = load_ui_state(path)

    assert loaded.mode == "single"
    assert loaded.input_folder == "input"


def test_load_pipeline_state_coerces_malformed_values(tmp_path) -> None:
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        json.dumps(
            {
                "version": "invalid",
                "updated_at": 123,
                "documents": {
                    "sha256:test": {
                        "content_hash": "sha256:test",
                        "file_name": "doc.pdf",
                        "relative_path": "doc.pdf",
                        "attempts": "NaN",
                        "failed_attempts": object(),
                        "artifacts": {
                            "optimizer_raw_paths": ["raw.json", 2, ""],
                            "optimizer_page_image_paths": None,
                            "interpreter_request_path": 123,
                        },
                    }
                },
            },
            default=str,
        ),
        encoding="utf-8",
    )

    loaded = load_pipeline_state(path)
    record = loaded.documents["sha256:test"]

    assert loaded.version == 1
    assert loaded.updated_at == "123"
    assert record.attempts == 0
    assert record.failed_attempts == 0
    assert record.artifacts.optimizer_raw_paths == ["raw.json", "2"]
    assert record.artifacts.optimizer_page_image_paths == []
    assert record.artifacts.interpreter_request_path == "123"


@pytest.mark.parametrize(
    ("loader", "factory_name", "expected_type", "warning_snippet", "path_name"),
    [
        (load_ui_state, "UiState", "UiState", "UI state could not be deserialized", "state.json"),
        (
            load_pipeline_state,
            "PipelineState",
            "PipelineState",
            "Pipeline state could not be deserialized",
            "state.json",
        ),
    ],
)
def test_state_loaders_fall_back_to_defaults_on_schema_error(
    tmp_path,
    monkeypatch,
    caplog,
    loader,
    factory_name: str,
    expected_type: str,
    warning_snippet: str,
    path_name: str,
) -> None:
    path = tmp_path / path_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    def _raise(_cls, _data):
        raise ValueError("bad schema")

    monkeypatch.setattr(getattr(state_module, factory_name), "from_dict", classmethod(_raise))
    caplog.set_level(logging.WARNING, logger=state_module.__name__)

    loaded = loader(path)

    assert type(loaded).__name__ == expected_type
    assert warning_snippet in caplog.text


def test_atomic_json_write_removes_temp_file_on_replace_failure(tmp_path, monkeypatch) -> None:
    path = tmp_path / "pipeline_state.json"

    def _fail_replace(_source, _target):
        raise OSError("replace failed")

    monkeypatch.setattr(state_adapter.os, "replace", _fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        atomic_json_write(path, {"ok": True})

    assert not list(tmp_path.glob(".pipeline_state.*.json.tmp"))
    assert not path.exists()


def test_file_lock_rejects_concurrent_acquire_and_release_is_idempotent(tmp_path) -> None:
    lock_path = tmp_path / "orchestrator.lock"
    first = FileLock(lock_path)
    second = FileLock(lock_path)

    first.acquire()
    with pytest.raises(FileLockBusyError):
        second.acquire()

    first.release()
    first.release()

    second.acquire()
    second.release()

