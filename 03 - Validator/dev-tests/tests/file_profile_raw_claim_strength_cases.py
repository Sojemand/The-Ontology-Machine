from __future__ import annotations

from pathlib import Path

from validator_vision.models import ValidatorConfig
from validator_vision.validator import DocumentValidator
from validator_vision.validator.planning import build_validation_target
from validator_vision.validator.raw_claims import collect_raw_claims

from file_profile_fixtures import file_raw, file_structured, report_path, write_json


def test_file_profile_downgrades_single_digit_label_suffix_claims_to_warn(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "tax-labels.structured.json",
        file_structured(
            content_hash="sha256:file-tax-label-suffix",
            fields={
                "page_label": "Seite 2",
                "net_amount": "278,50",
                "vat_label": "USt.1",
                "vat_rate": "19,00%",
                "vat_amount": "52,92",
                "total_amount": "331,42",
            },
            rows=[],
            free_text="Netto 278,50 USt.1 19,00% USt. 52,92 EUR Endbetrag 331,42",
        ),
    )
    raw_payload = file_raw(
        content_hash="sha256:file-tax-label-suffix",
        sections=[
            "Netto",
            "USt.1",
            "USt.",
            "19,00%",
            "Netto",
            "USt.2",
            "USt.",
            "%",
            "Netto",
            "USt.0",
            "Endbetrag",
            "278,50",
            "52,92",
            "EUR",
            "331,42",
        ],
    )
    raw_path = write_json(
        scratch_dir / "tax-labels.raw.json",
        raw_payload,
    )
    raw_claims = collect_raw_claims(raw_payload)

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "WARN"
    assert report.checks["numeric_claims"].status == "WARN"
    assert report.summary.fail_count == 0
    assert {issue.level for issue in report.issues} == {"WARN"}
    assert {issue.extracted_value for issue in report.issues} == {"0"}
    assert raw_claims["num:0"].strength == "weak"
    assert raw_claims["num:1"].strength == "weak"
    assert raw_claims["num:2"].strength == "weak"


def test_file_profile_ignores_raw_blocks_without_numeric_or_date_claims(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "ocr-backed-source.structured.json",
        file_structured(content_hash="sha256:file-source-ocr", fields={}, rows=[], free_text=""),
    )
    raw_path = write_json(
        scratch_dir / "ocr-backed-source.raw.json",
        file_raw(
            content_hash="sha256:file-source-ocr",
            sections=[
                {
                    "id": "page1_para_0",
                    "page": 1,
                    "text": "noise text",
                }
            ],
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "PASS"
    assert report.checks["numeric_claims"].checked == 0
    assert report.checks["numeric_claims"].valid == 0


def test_file_build_validation_target_accepts_explicit_raw(scratch_dir: Path, tmp_report_root: Path):
    structured_path = write_json(
        scratch_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-target",
            fields={"gross_amount": 318.79},
            rows=[],
            free_text="Gesamtbetrag 318,79 EUR",
        ),
    )
    raw_path = write_json(
        scratch_dir / "invoice.raw.json",
        file_raw(content_hash="sha256:file-target", sections=["Gesamtbetrag 318,79 EUR"]),
    )

    target = build_validation_target(structured_path, report_path(tmp_report_root, structured_path), raw_path=raw_path)

    assert target.raw_path == raw_path
