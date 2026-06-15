from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from corpus_builder.models import atomic_json_write

from .models_support import _link_or_skip


def test_atomic_json_write_handles_concurrent_writers(tmp_path: Path):
    output_path = tmp_path / "ui_state.json"
    barrier = threading.Barrier(12)
    errors: list[BaseException] = []

    def _worker(index: int) -> None:
        try:
            barrier.wait()
            atomic_json_write(output_path, {"index": index})
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_worker, args=(index,)) for index in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert isinstance(payload["index"], int)


def test_atomic_json_write_replaces_final_path_without_mutating_hardlinks(tmp_path: Path):
    output_path = tmp_path / "state.json"
    output_path.write_text('{"before": true}', encoding="utf-8")
    hardlink_path = tmp_path / "state.alias.json"
    _link_or_skip(output_path, hardlink_path)

    atomic_json_write(output_path, {"after": True})

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"after": True}
    assert hardlink_path.read_text(encoding="utf-8") == '{"before": true}'


def test_atomic_json_write_uses_short_temp_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, object]] = []
    real_mkstemp = __import__("tempfile").mkstemp

    def capture_mkstemp(*args, **kwargs):
        calls.append(dict(kwargs))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr("corpus_builder.models.serialization.tempfile.mkstemp", capture_mkstemp)
    target = tmp_path / f"{'long_name_' * 20}.json"

    atomic_json_write(target, {"ok": True})

    assert calls
    assert calls[0]["prefix"] == "."
    assert calls[0]["suffix"] == ".tmp"
    assert str(calls[0]["dir"]).replace("\\\\?\\", "") == str(target.parent.resolve())
    assert str(calls[0]["prefix"]) not in target.stem
