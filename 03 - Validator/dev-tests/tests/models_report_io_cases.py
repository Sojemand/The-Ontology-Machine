from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path

import pytest

from validator_vision.models import ValidationReport, atomic_json_write, load_report, report_name


def test_atomic_json_write_cleans_up_tmp_file(scratch_dir: Path):
    target = scratch_dir / "test.json"
    with pytest.raises(TypeError):
        atomic_json_write(target, {"broken": object()})
    assert list(scratch_dir.glob("*.tmp")) == []


def test_atomic_json_write_cleans_up_tmp_file_when_replace_fails(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path):
    target = scratch_dir / "test.json"

    def _raise(*_args, **_kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr("validator_vision.models.report_io._replace_file_with_retry", _raise)
    with pytest.raises(PermissionError, match="locked"):
        atomic_json_write(target, {"ok": True})

    assert list(scratch_dir.glob("*.tmp")) == []


def test_atomic_json_write_handles_same_target_concurrency(scratch_dir: Path):
    target = scratch_dir / "race.json"
    barrier = threading.Barrier(8)
    errors: list[str] = []

    def _write(worker_id: int) -> None:
        try:
            barrier.wait()
            atomic_json_write(target, {"worker": worker_id})
        except Exception as exc:  # pragma: no cover - failure path asserted below
            errors.append(repr(exc))

    threads = [threading.Thread(target=_write, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert isinstance(payload["worker"], int)


def test_report_helpers_roundtrip(scratch_dir: Path):
    report = ValidationReport(file_name="invoice.pdf", result="PASS", interpreter_profile="vision")
    report_path = scratch_dir / "invoice.vision_validation_report.json"
    atomic_json_write(report_path, report.to_dict())
    loaded = load_report(report_path)
    assert loaded.file_name == "invoice.pdf"
    assert loaded.result == "PASS"
    assert report_name(Path("invoice.structured.json")) == "invoice.vision_validation_report.json"
    assert report_name(Path("invoice.structured.json"), "file") == "invoice.files_validation_report.json"
    assert report_name(Path("invoice.structured.json"), "table") == "invoice.vision_validation_report.json"


def test_report_name_shortens_long_structured_names_for_windows_path_budget():
    long_name = "a" * 226 + ".structured.json"
    other_long_name = "b" * 226 + ".structured.json"

    report = report_name(Path(long_name), "vision")

    assert len(report) <= 120
    assert report.endswith(".vision_validation_report.json")
    assert report.startswith("a")
    assert "-" in report.removesuffix(".vision_validation_report.json")
    assert report != report_name(Path(other_long_name), "vision")


def test_atomic_json_write_uses_short_temp_prefix_for_long_report_names(scratch_dir: Path, monkeypatch: pytest.MonkeyPatch):
    report_path = scratch_dir / ("x" * 60 + ".vision_validation_report.json")
    captured: dict[str, str] = {}
    original_mkstemp = tempfile.mkstemp

    def _mkstemp(*args, **kwargs):
        captured["prefix"] = kwargs["prefix"]
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr("validator_vision.models.report_io.tempfile.mkstemp", _mkstemp)
    atomic_json_write(report_path, {"ok": True})

    assert report_path.exists()
    assert len(captured["prefix"]) == 10
    assert "x" not in captured["prefix"]


def test_validation_report_from_dict_ignores_non_object_entries():
    report = ValidationReport.from_dict(
        {
            "file_name": "invoice.pdf",
            "checks": {"ok": {"status": "PASS"}, "broken": "x"},
            "issues": [{"check": "rows", "level": "WARN", "field": "field", "message": "msg"}, "broken"],
            "summary": [],
        }
    )

    assert report.file_name == "invoice.pdf"
    assert list(report.checks) == ["ok"]
    assert len(report.issues) == 1
    assert report.summary.total_issues == 0
