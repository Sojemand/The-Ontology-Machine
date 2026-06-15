from __future__ import annotations

import json
from pathlib import Path

from validator_vision.orchestrator_contract import healthcheck, main as contract_main, validate_document

from contract_fixtures import TEST_DATA, report_path as fixture_report_path


def test_contract_validate_document(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    report_path = fixture_report_path(scratch_dir, "invoice_ok.vision_validation_report.json")
    request_path.write_text(
        json.dumps(
            {
                "action": "validate_document",
                "structured_path": str(TEST_DATA / "invoice_ok.structured.json"),
                "validation_output_path": str(report_path),
            }
        ),
        encoding="utf-8",
    )
    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "PASS"
    assert Path(payload["report_path"]) == report_path
    assert report_path.exists()


def test_contract_unknown_action_returns_error(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    request_path.write_text(json.dumps({"action": "unknown"}), encoding="utf-8")
    contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ERROR"


def test_contract_missing_action_returns_error(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    request_path.write_text(json.dumps({}), encoding="utf-8")

    contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ERROR"
    assert payload["error"] == "action fehlt oder ist ungueltig."


def test_contract_healthcheck_returns_ok(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    request_path.write_text(json.dumps({"action": "healthcheck"}), encoding="utf-8")

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["healthy"] is True
    assert payload["dependencies"] == [
        {"name": "config", "kind": "config", "required": True, "healthy": True, "detail": "ok"}
    ]


def test_contract_surface_healthcheck_returns_ok() -> None:
    payload = healthcheck()

    assert payload["status"] == "ok"
    assert payload["healthy"] is True
    assert payload["dependencies"] == [
        {"name": "config", "kind": "config", "required": True, "healthy": True, "detail": "ok"}
    ]


def test_contract_rejects_missing_structured_path(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    request_path.write_text(
        json.dumps(
            {
                "action": "validate_document",
                "validation_output_path": str(fixture_report_path(scratch_dir, "invoice_ok.vision_validation_report.json")),
            }
        ),
        encoding="utf-8",
    )

    contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ERROR"
    assert "structured_path" in payload["error"]


def test_contract_rejects_legacy_output_dir_field(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    request_path.write_text(
        json.dumps(
            {
                "action": "validate_document",
                "structured_path": str(TEST_DATA / "invoice_ok.structured.json"),
                "output_dir": str(scratch_dir / "reports"),
            }
        ),
        encoding="utf-8",
    )

    contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ERROR"
    assert payload["error"] == "Legacy-Feld nicht erlaubt: output_dir"


def test_contract_rejects_validation_output_path_when_it_is_a_directory(scratch_dir: Path):
    request_path = scratch_dir / "request.json"
    response_path = scratch_dir / "response.json"
    report_dir = scratch_dir / "reports"
    report_dir.mkdir()
    request_path.write_text(
        json.dumps(
            {
                "action": "validate_document",
                "structured_path": str(TEST_DATA / "invoice_ok.structured.json"),
                "validation_output_path": str(report_dir),
            }
        ),
        encoding="utf-8",
    )

    contract_main(["--request", str(request_path), "--response", str(response_path)])
    payload = json.loads(response_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ERROR"
    assert "validation_output_path muss eine Datei sein" in payload["error"]


def test_contract_rejects_legacy_raw_root(scratch_dir: Path):
    payload = validate_document(
        {
            "action": "validate_document",
            "structured_path": str(TEST_DATA / "invoice_ok.structured.json"),
            "validation_output_path": str(fixture_report_path(scratch_dir, "invoice_ok.vision_validation_report.json")),
            "raw_root": str(scratch_dir / "raw"),
        }
    )

    assert payload["status"] == "ERROR"
    assert payload["error"] == "Legacy-Feld nicht erlaubt: raw_root"
