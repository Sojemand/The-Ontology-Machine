from __future__ import annotations

from pathlib import Path

import pytest

from validator_vision.models import ValidatorConfig
from validator_vision.validator import DocumentValidator
from validator_vision.validator.planning import plan_batch_targets

from file_profile_fixtures import file_raw, file_structured, report_path, write_json


def test_file_profile_passes_when_raw_numeric_claims_survive_anywhere_in_structured(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-pass",
            context={"document_date": "2024-03-15"},
            fields={"net_amount": 267.89},
            rows=[{"tax_amount": 50.90}],
            free_text="Rechnung vom 15.03.2024\nGesamt 318,79 EUR",
            segments=[{"segment_id": "Page1_Segment1", "text": "Gesamtbetrag 318,79 EUR"}],
        ),
    )
    raw_path = write_json(
        scratch_dir / "invoice.raw.json",
        file_raw(
            content_hash="sha256:file-pass",
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

    assert report.interpreter_profile == "file"
    assert report.result == "PASS"
    assert set(report.checks) == {"numeric_claims"}
    assert report.checks["numeric_claims"].checked == 4
    assert report.checks["numeric_claims"].valid == 4


def test_file_profile_deduplicates_repeated_raw_numeric_claims(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-dedup",
            fields={},
            rows=[],
            free_text="Gesamtbetrag 318,79 EUR",
            segments=[{"segment_id": "Page1_Segment1", "text": "318,79 EUR"}],
        ),
    )
    raw_path = write_json(
        scratch_dir / "invoice.raw.json",
        file_raw(
            content_hash="sha256:file-dedup",
            sections=["Gesamtbetrag 318,79 EUR", "Nochmals 318,79 EUR"],
            facts={"gross_amount": {"value": 318.79}},
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "PASS"
    assert report.checks["numeric_claims"].checked == 1
    assert report.checks["numeric_claims"].valid == 1


def test_file_profile_fails_when_raw_numeric_claim_is_missing_from_structured(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-fail",
            fields={"gross_amount": 318.79},
            rows=[],
            free_text="Gesamtbetrag 318,79 EUR",
        ),
    )
    raw_path = write_json(
        scratch_dir / "invoice.raw.json",
        file_raw(
            content_hash="sha256:file-fail",
            sections=["Belegdatum 2024-03-15", "Gesamtbetrag 318,79 EUR"],
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "FAIL"
    assert report.checks["numeric_claims"].status == "FAIL"
    assert report.issues[0].field == "ocr_reference.blocks[0].value"
    assert report.issues[0].extracted_value == "2024-03-15"


def test_file_profile_requires_raw_evidence(scratch_dir: Path, tmp_report_root: Path):
    structured_path = write_json(
        scratch_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-missing-raw",
            fields={"gross_amount": 318.79},
            rows=[],
            free_text="Gesamtbetrag 318,79 EUR",
        ),
    )

    with pytest.raises(ValueError, match="Raw-Evidence"):
        DocumentValidator(ValidatorConfig()).validate(
            structured_path,
            report_path(tmp_report_root, structured_path),
        )


def test_file_batch_planning_resolves_raw_from_raw_root(scratch_dir: Path, tmp_report_root: Path):
    structured_dir = scratch_dir / "structured"
    raw_root = scratch_dir / "raw"
    nested_dir = structured_dir / "nested"
    nested_dir.mkdir(parents=True)
    raw_root.mkdir(parents=True)
    structured_path = write_json(
        nested_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-batch",
            fields={"gross_amount": 318.79},
            rows=[],
            free_text="Gesamtbetrag 318,79 EUR",
        ),
    )
    raw_path = write_json(
        raw_root / "invoice.raw.json",
        file_raw(content_hash="sha256:file-batch", sections=["Gesamtbetrag 318,79 EUR"]),
    )

    targets = plan_batch_targets(structured_dir, tmp_report_root, raw_root=raw_root)

    assert len(targets) == 1
    assert targets[0].structured_path == structured_path
    assert targets[0].report_path == tmp_report_root / "nested" / "invoice.files_validation_report.json"
    assert targets[0].raw_path == raw_path
