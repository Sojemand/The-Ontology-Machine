from __future__ import annotations

import json
from pathlib import Path

import validator_vision.orchestrator_contract as contract_module
from validator_vision.models import ValidationReport
from validator_vision.orchestrator_contract import debug_run, validate_document

from contract_fixtures import TEST_DATA, debug_payload, file_raw, file_structured, report_path, write_json


def test_contract_validate_document_supports_file_profile_with_raw_path(scratch_dir: Path):
    structured_path = write_json(scratch_dir / "transport.structured.json", file_structured(content_hash="sha256:file-contract"))
    raw_path = write_json(scratch_dir / "transport.raw.json", file_raw(content_hash="sha256:file-contract"))
    payload = validate_document(
        {
            "action": "validate_document",
            "structured_path": str(structured_path),
            "validation_output_path": str(report_path(scratch_dir, "transport.files_validation_report.json")),
            "raw_path": str(raw_path),
        }
    )
    assert payload["status"] == "PASS"
    assert Path(payload["report_path"]).exists()


def test_contract_debug_run_rejects_output_root_outside_session(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    payload = debug_run(
        debug_payload(
            session_root,
            mode="single",
            source_path=str(TEST_DATA / "invoice_ok.structured.json"),
            output_root=str(scratch_dir / "outside"),
        )
    )
    assert payload["status"] == "ERROR"
    assert "output_root muss innerhalb von session_root liegen" in payload["error"]
    assert not (scratch_dir / "outside").exists()


def test_contract_debug_run_single_rejects_non_string_input_root(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    payload = debug_run(
        debug_payload(
            session_root,
            mode="single",
            source_path=str(TEST_DATA / "invoice_ok.structured.json"),
            input_root={"broken": True},
        )
    )

    assert payload["status"] == "ERROR"
    assert "Pfadoptionen muessen Strings sein" in payload["error"]


def test_contract_debug_run_single_writes_session_artifacts(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    payload = debug_run(
        debug_payload(
            session_root,
            mode="single",
            source_path=str(TEST_DATA / "invoice_ok.structured.json"),
        )
    )
    assert payload["status"] == "ok"
    assert (session_root / "snapshot.json").exists()
    assert (session_root / "result.json").exists()
    assert (session_root / "run.log").exists()
    assert (session_root / "outputs" / "config_snapshot.json").exists()
    assert (session_root / "outputs" / "report_index.json").exists()
    report_paths = payload["outputs"]["validation_reports"]
    assert len(report_paths) == 1
    assert (session_root / report_paths[0]).exists()


def test_contract_debug_run_single_file_profile_accepts_raw_path(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    structured_path = write_json(scratch_dir / "transport.structured.json", file_structured(content_hash="sha256:file-debug"))
    raw_path = write_json(scratch_dir / "transport.raw.json", file_raw(content_hash="sha256:file-debug"))

    payload = debug_run(
        debug_payload(
            session_root,
            mode="single",
            source_path=str(structured_path),
            options={
                "raw_evidence": {"raw_path": str(raw_path)},
                "check_toggles": {
                    "free_text": True,
                    "context_scalars": True,
                    "content_fields": True,
                    "rows": True,
                },
            },
        )
    )

    assert payload["status"] == "ok"
    assert len(payload["outputs"]["validation_reports"]) == 1


def test_contract_debug_run_rejects_file_profile_without_raw(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    structured_path = write_json(scratch_dir / "transport.structured.json", file_structured(content_hash="sha256:file-debug"))

    payload = debug_run(debug_payload(session_root, mode="single", source_path=str(structured_path)))

    assert payload["status"] == "error"
    assert "Raw-Evidence" in payload["error"]


def test_contract_debug_run_batch_uses_raw_root_and_writes_counts(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    structured_dir = scratch_dir / "structured"
    raw_root = scratch_dir / "raw"
    structured_dir.mkdir()
    raw_root.mkdir()
    write_json(structured_dir / "vision.structured.json", json.loads((TEST_DATA / "invoice_ok.structured.json").read_text(encoding="utf-8")))
    write_json(structured_dir / "file.structured.json", file_structured(content_hash="sha256:file-batch"))
    write_json(raw_root / "transport.raw.json", file_raw(content_hash="sha256:file-batch"))

    payload = debug_run(
        debug_payload(
            session_root,
            mode="batch",
            input_root=str(structured_dir),
            options={
                "raw_evidence": {"raw_root": str(raw_root)},
                "check_toggles": {
                    "free_text": True,
                    "context_scalars": True,
                    "content_fields": True,
                    "rows": True,
                },
            },
        )
    )

    index = json.loads((session_root / "outputs" / "report_index.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["metrics"]["reports_total"] == 2
    assert len(index["reports"]) == 2


def test_contract_debug_run_indexes_only_current_reports(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    stale_report = session_root / "outputs" / "validation_reports" / "stale.vision_validation_report.json"
    stale_report.parent.mkdir(parents=True)
    stale_report.write_text("{", encoding="utf-8")

    payload = debug_run(
        debug_payload(
            session_root,
            mode="single",
            source_path=str(TEST_DATA / "invoice_ok.structured.json"),
        )
    )

    index = json.loads((session_root / "outputs" / "report_index.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["metrics"]["reports_total"] == 1
    assert len(index["reports"]) == 1
    assert index["reports"][0]["path"] != "outputs/validation_reports/stale.vision_validation_report.json"
    assert payload["outputs"]["validation_reports"] == [index["reports"][0]["path"]]


def test_contract_debug_run_persists_check_toggle_overrides(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"

    payload = debug_run(
        debug_payload(
            session_root,
            mode="single",
            source_path=str(TEST_DATA / "invoice_ok.structured.json"),
            options={
                "raw_evidence": {},
                "check_toggles": {
                    "free_text": False,
                    "context_scalars": False,
                    "content_fields": True,
                    "rows": False,
                },
            },
        )
    )

    config_snapshot = json.loads((session_root / "outputs" / "config_snapshot.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert config_snapshot["checks"] == {
        "free_text": False,
        "context_scalars": False,
        "content_fields": True,
        "rows": False,
    }


def test_contract_debug_run_marks_session_cancelled_with_partial_outputs(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(scratch_dir / "validator-home"))
    session_root = scratch_dir / "session"
    structured_dir = scratch_dir / "structured"
    structured_dir.mkdir()
    write_json(structured_dir / "vision_a.structured.json", json.loads((TEST_DATA / "invoice_ok.structured.json").read_text(encoding="utf-8")))
    write_json(structured_dir / "vision_b.structured.json", json.loads((TEST_DATA / "minutes_ok.structured.json").read_text(encoding="utf-8")))

    class _CancellingValidator:
        def __init__(self, _config) -> None:
            return None

        def validate(self, structured_path: Path, report_path: Path, *, raw_path: Path | None = None) -> ValidationReport:
            del raw_path
            if not (session_root / "cancel.request").exists():
                (session_root / "cancel.request").write_text("stop", encoding="utf-8")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            payload = ValidationReport(file_name=structured_path.name, file_path=str(report_path), result="PASS")
            report_path.write_text(json.dumps(payload.to_dict()), encoding="utf-8")
            return payload

    monkeypatch.setattr(contract_module, "DocumentValidator", _CancellingValidator)

    payload = contract_module.debug_run(debug_payload(session_root, mode="batch", input_root=str(structured_dir)))

    result = json.loads((session_root / "result.json").read_text(encoding="utf-8"))
    log_text = (session_root / "run.log").read_text(encoding="utf-8")
    assert payload["status"] == "cancelled"
    assert result["status"] == "cancelled"
    assert payload["metrics"]["reports_total"] == 1
    assert "[CANCELLED]" in log_text
