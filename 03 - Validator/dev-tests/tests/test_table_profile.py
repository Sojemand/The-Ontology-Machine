from __future__ import annotations

from pathlib import Path

import pytest

from validator_vision.models import ValidatorConfig, report_name
from validator_vision.validator import DocumentValidator

from file_profile_fixtures import write_json


def table_structured(*, content_hash: str) -> dict:
    return {
        "schema_version": "1.0",
        "processing": {"interpreter_profile": "table"},
        "content": {
            "fields": {"statement_date": "2024-02-01", "total": 100.0},
            "rows": [{"date": "2024-02-01", "amount": 100.0}],
            "free_text": "Deterministic spreadsheet export",
        },
        "source": {"file_name": "sheet.xlsx", "content_hash": content_hash},
    }


def table_raw(*, content_hash: str) -> dict:
    return {
        "doc": {"file_name": "sheet.xlsx", "content_hash": content_hash},
        "deterministic_extract": {
            "tables_base": [
                {
                    "rows_base": [
                        {"cells": [{"value": "2024-02-01"}, {"value": "100,00 EUR"}]},
                    ]
                }
            ]
        },
    }


def test_table_profile_validates_deterministic_extract_tables(scratch_dir: Path, tmp_report_root: Path):
    structured_path = write_json(
        scratch_dir / "sheet.structured.json",
        table_structured(content_hash="sha256:table-pass"),
    )
    raw_path = write_json(scratch_dir / "sheet.raw.json", table_raw(content_hash="sha256:table-pass"))
    report_path = tmp_report_root / report_name(structured_path, "table")

    report = DocumentValidator(ValidatorConfig()).validate(structured_path, report_path, raw_path=raw_path)

    assert report.interpreter_profile == "table"
    assert report.result == "PASS"
    assert set(report.checks) == {"free_text", "numeric_claims"}
    assert report.checks["numeric_claims"].checked == 2
    assert report_path.name == "sheet.vision_validation_report.json"


def test_table_profile_requires_raw_evidence(scratch_dir: Path, tmp_report_root: Path):
    structured_path = write_json(
        scratch_dir / "sheet.structured.json",
        table_structured(content_hash="sha256:table-missing-raw"),
    )

    with pytest.raises(ValueError, match="Table-Profil benoetigt Raw-Evidence"):
        DocumentValidator(ValidatorConfig()).validate(
            structured_path,
            tmp_report_root / report_name(structured_path, "table"),
        )
