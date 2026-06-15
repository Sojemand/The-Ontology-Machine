from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from validator_vision.models import ValidatorConfig, report_name
from validator_vision.validator import DocumentValidator

from file_profile_fixtures import file_raw, file_structured, report_path, write_json

TEST_DATA = Path(__file__).parent / "test_data"


def _stable_report(report) -> dict:
    return {
        "interpreter_profile": report.interpreter_profile,
        "file_name": report.file_name,
        "content_hash": report.content_hash,
        "result": report.result,
        "needs_review": report.needs_review,
        "summary": asdict(report.summary),
        "checks": {name: asdict(value) for name, value in report.checks.items()},
        "issues": [asdict(issue) for issue in report.issues],
    }


def _expected(name: str) -> dict:
    return json.loads((TEST_DATA / name).read_text(encoding="utf-8"))


def test_golden_vision_invoice_report(default_config, tmp_report_root: Path):
    structured_path = TEST_DATA / "invoice_ok.structured.json"
    report = DocumentValidator(default_config).validate(
        structured_path,
        tmp_report_root / report_name(structured_path, "vision"),
    )

    assert _stable_report(report) == _expected("golden_vision_invoice_ok.report.json")


def test_golden_file_transport_report(tmp_report_root: Path, scratch_dir: Path):
    structured_path = write_json(
        scratch_dir / "transport.structured.json",
        file_structured(
            content_hash="sha256:golden-file",
            context={"document_date": "2024-03-15"},
            fields={"net_amount": 267.89},
            rows=[{"tax_amount": 50.90}],
            free_text="Rechnung vom 15.03.2024\nGesamt 318,79 EUR",
            segments=[{"segment_id": "Page1_Segment1", "text": "Gesamtbetrag 318,79 EUR"}],
        ),
    )
    raw_path = write_json(
        scratch_dir / "transport.raw.json",
        file_raw(
            content_hash="sha256:golden-file",
            ctx={"document_date": "2024-03-15"},
            sections=["Rechnung vom 15.03.2024\nGesamt 318,79 EUR"],
            facts={"net_amount": {"value": 267.89}},
            tables=[{"page": 1, "rows": [["50,90 EUR"]]}],
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert _stable_report(report) == _expected("golden_file_transport.report.json")


def test_golden_table_sheet_report(tmp_report_root: Path, scratch_dir: Path):
    structured_path = write_json(
        scratch_dir / "sheet.structured.json",
        {
            "schema_version": "1.0",
            "processing": {"interpreter_profile": "table"},
            "content": {
                "fields": {"statement_date": "2024-02-01", "total": 100.0},
                "rows": [{"date": "2024-02-01", "amount": 100.0}],
                "free_text": "Deterministic spreadsheet export",
            },
            "source": {"file_name": "sheet.xlsx", "content_hash": "sha256:golden-table"},
        },
    )
    raw_path = write_json(
        scratch_dir / "sheet.raw.json",
        {
            "doc": {"file_name": "sheet.xlsx", "content_hash": "sha256:golden-table"},
            "deterministic_extract": {
                "tables_base": [
                    {"rows_base": [{"cells": [{"value": "2024-02-01"}, {"value": "100,00 EUR"}]}]}
                ]
            },
        },
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        tmp_report_root / report_name(structured_path, "table"),
        raw_path=raw_path,
    )

    assert _stable_report(report) == _expected("golden_table_sheet.report.json")
