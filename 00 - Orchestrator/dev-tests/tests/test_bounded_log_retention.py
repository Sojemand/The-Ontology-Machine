from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator import bounded_log
from orchestrator.debug_host import polling
from orchestrator.pipeline import debug


def test_pipeline_append_log_bounds_active_and_document_logs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(debug, "PIPELINE_LOG_BYTES_HARD_CAP", 160)
    engine = SimpleNamespace(
        _active_log_path=tmp_path / "run.log",
        _runtime_lock=None,
        _thread_local=None,
        _log_callback=None,
    )
    document_log_path = tmp_path / "doc.run.log"

    for index in range(12):
        debug.append_log(engine, f"line-{index:02d} " + "x" * 24, document_log_path=document_log_path)

    for path in (engine._active_log_path, document_log_path):
        text = path.read_text(encoding="utf-8")
        assert len(path.read_bytes()) <= 160
        assert "log truncated" in text
        assert "line-11" in text


def test_debug_host_append_log_is_bounded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(polling, "DEBUG_HOST_LOG_BYTES_HARD_CAP", 150)
    log_path = tmp_path / "run.log"

    for index in range(12):
        polling.append_log(log_path, f"debug-{index:02d} " + "y" * 24)

    text = log_path.read_text(encoding="utf-8")
    assert len(log_path.read_bytes()) <= 150
    assert "log truncated" in text
    assert "debug-11" in text


def test_bounded_log_handles_single_append_near_limit(tmp_path: Path) -> None:
    log_path = tmp_path / "run.log"
    log_path.write_text("old\n" * 50, encoding="utf-8")

    bounded_log.append_text(log_path, "z" * 95, max_bytes=100)

    assert len(log_path.read_bytes()) <= 100
    assert log_path.read_text(encoding="utf-8") == "z" * 95
