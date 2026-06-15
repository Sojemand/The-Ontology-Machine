from __future__ import annotations

from pathlib import Path

from validator_vision.models import ValidatorConfig
from validator_vision.validator import DocumentValidator

from file_profile_fixtures import file_raw, file_structured, report_path, write_json


def test_file_profile_ignores_extra_structured_numeric_claims_that_are_not_in_raw(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "invoice.structured.json",
        file_structured(
            content_hash="sha256:file-structured-extra",
            fields={"gross_amount": 318.79, "discount_amount": 10.00},
            rows=[],
            free_text="Gesamtbetrag 318,79 EUR\nSkonto 10,00 EUR",
        ),
    )
    raw_path = write_json(
        scratch_dir / "invoice.raw.json",
        file_raw(content_hash="sha256:file-structured-extra", sections=["Gesamtbetrag 318,79 EUR"]),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "PASS"
    assert report.checks["numeric_claims"].checked == 1
    assert report.checks["numeric_claims"].valid == 1


def test_file_profile_validates_dates_from_raw_sections_against_structured_fields(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "receipt.structured.json",
        file_structured(
            content_hash="sha256:file-section-date",
            fields={"receipt_confirmation_date": "2022-05-19"},
            rows=[],
            free_text="",
        ),
    )
    raw_path = write_json(
        scratch_dir / "receipt.raw.json",
        file_raw(
            content_hash="sha256:file-section-date",
            sections=["Sendung uebernommen, 2022-05-19: Schmidt Transporte"],
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


def test_file_profile_reads_claims_from_raw_blocks(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "mixed.structured.json",
        file_structured(
            content_hash="sha256:file-source-only",
            fields={"receipt_confirmation_date": "2022-05-19"},
            rows=[],
            free_text="",
        ),
    )
    raw_path = write_json(
        scratch_dir / "mixed.raw.json",
        file_raw(
            content_hash="sha256:file-source-only",
            sections=[
                {"id": "page1_para_0", "page": 1, "text": "Sendung uebernommen, 2022-05-19"},
            ],
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


def test_file_profile_accepts_layout_split_table_values_in_structured_rows(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "table-line.structured.json",
        file_structured(
            content_hash="sha256:file-layout-table-line",
            fields={},
            rows=[
                {
                    "product_id": "38",
                    "product_name": "Cote de Blaye",
                    "quantity": "20",
                    "unit_price": "210.8",
                }
            ],
            free_text="",
        ),
    )
    raw_path = write_json(
        scratch_dir / "table-line.raw.json",
        file_raw(
            content_hash="sha256:file-layout-table-line",
            sections=["38\nCote de Blaye\n20\n210.8"],
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "PASS"
    assert report.checks["numeric_claims"].checked == 3
    assert report.checks["numeric_claims"].valid == 3


def test_file_profile_matches_address_numbers_embedded_in_structured_field(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "address.structured.json",
        file_structured(
            content_hash="sha256:file-address",
            fields={"address": "BorgfeldtstraÃŸe 15, 07607 Eisenberg"},
            rows=[],
            free_text="",
        ),
    )
    raw_path = write_json(
        scratch_dir / "address.raw.json",
        file_raw(
            content_hash="sha256:file-address",
            sections=["BorgfeldtstraÃŸe 15", "07607 Eisenberg"],
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "PASS"
    assert report.checks["numeric_claims"].checked == 2
    assert report.checks["numeric_claims"].valid == 2


def test_file_profile_downgrades_dirty_raw_numeric_claims_to_warn(
    scratch_dir: Path,
    tmp_report_root: Path,
):
    structured_path = write_json(
        scratch_dir / "dirty.structured.json",
        file_structured(
            content_hash="sha256:file-dirty-raw",
            fields={},
            rows=[],
            free_text="",
        ),
    )
    raw_path = write_json(
        scratch_dir / "dirty.raw.json",
        file_raw(
            content_hash="sha256:file-dirty-raw",
            sections=["OCR noise \x00\x01 99999"],
        ),
    )

    report = DocumentValidator(ValidatorConfig()).validate(
        structured_path,
        report_path(tmp_report_root, structured_path),
        raw_path=raw_path,
    )

    assert report.result == "WARN"
    assert report.checks["numeric_claims"].status == "WARN"
    assert report.summary.fail_count == 0
    assert report.summary.warn_count == 1
    assert report.issues[0].level == "WARN"
