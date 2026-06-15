from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator_vision.models import (
    CheckToggles,
    MatchConfig,
    ValidationReport,
    ValidatorConfig,
    load_report,
    report_name,
)
from validator_vision.validator import DocumentValidator
from validator_vision.validator.planning import plan_batch_targets

TEST_DATA = Path(__file__).parent / "test_data"


def _write_structured(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = dict(payload)
    processing = materialized.get("processing")
    if not isinstance(processing, dict):
        processing = {}
    processing.setdefault("interpreter_profile", "vision")
    materialized["processing"] = processing
    path.write_text(json.dumps(materialized, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _report_path(report_root: Path, structured_path: Path, interpreter_profile: str = "vision") -> Path:
    return report_root / report_name(structured_path, interpreter_profile)


def test_validate_passes_for_reference_data(default_config, tmp_report_root: Path):
    report_path = _report_path(tmp_report_root, TEST_DATA / "invoice_ok.structured.json")
    report = DocumentValidator(default_config).validate(TEST_DATA / "invoice_ok.structured.json", report_path)
    assert report.result == "PASS"
    assert report.file_name == "invoice_ok.pdf"
    assert report.summary.total_issues == 0
    assert report_path.exists()


def test_validate_handles_non_string_free_text_without_crashing(scratch_dir: Path, tmp_report_root: Path):
    structured_path = _write_structured(scratch_dir / "doc.structured.json", {"content": {"free_text": 42}})
    report = DocumentValidator(ValidatorConfig()).validate(structured_path, _report_path(tmp_report_root, structured_path))
    assert report.result == "FAIL"
    assert report.checks["free_text"].status == "FAIL"
    assert "context_scalars" not in report.checks


def test_validate_missing_text_skips_follow_up_checks(scratch_dir: Path, tmp_report_root: Path):
    structured_path = _write_structured(
        scratch_dir / "doc.structured.json",
        {
            "context": {"company": "Acme"},
            "content": {"free_text": "", "fields": {"invoice_number": "RG-1"}, "rows": [{"position": "Item"}]},
        },
    )
    report = DocumentValidator(ValidatorConfig()).validate(structured_path, _report_path(tmp_report_root, structured_path))
    assert report.result == "FAIL"
    assert set(report.checks) == {"free_text"}


def test_validate_batch_finds_nested_documents(default_config, scratch_dir: Path, tmp_report_root: Path):
    nested = scratch_dir / "nested"
    nested.mkdir()
    _write_structured(nested / "doc.structured.json", {"content": {"free_text": "Hello"}})
    targets = plan_batch_targets(scratch_dir, tmp_report_root)
    reports = DocumentValidator(default_config).validate_batch(targets)
    assert len(reports) == 1
    assert reports[0].file_name == "doc"
    assert (tmp_report_root / "nested" / "doc.vision_validation_report.json").exists()


def test_report_roundtrip_uses_central_loader(default_config, tmp_report_root: Path):
    validator = DocumentValidator(default_config)
    source = TEST_DATA / "minutes_ok.structured.json"
    report_path = _report_path(tmp_report_root, source)
    validator.validate(source, report_path)
    report = load_report(report_path)
    assert isinstance(report, ValidationReport)
    assert report.result == "PASS"


def test_invalid_json_object_raises(scratch_dir: Path, tmp_report_root: Path):
    broken = scratch_dir / "broken.structured.json"
    broken.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="kein JSON-Objekt|kein Objekt"):
        DocumentValidator(ValidatorConfig()).validate(broken, _report_path(tmp_report_root, broken))


def test_validate_limits_reported_issues_per_check(scratch_dir: Path, tmp_report_root: Path):
    structured_path = _write_structured(
        scratch_dir / "doc.structured.json",
        {
            "content": {
                "free_text": "Reference text",
                "fields": {
                    f"field_{index}": f"Missing value {index}"
                    for index in range(5)
                },
            }
        },
    )
    config = ValidatorConfig(
        checks=CheckToggles(free_text=True, context_scalars=False, content_fields=True, rows=False),
        match=MatchConfig(),
        max_issues_per_check=2,
    )

    report = DocumentValidator(config).validate(structured_path, _report_path(tmp_report_root, structured_path))

    assert report.result == "FAIL"
    assert report.summary.total_issues == 5
    assert report.checks["content_fields"].issue_count == 5
    assert len(report.issues) == 2


def test_validate_respects_disabled_checks(scratch_dir: Path, tmp_report_root: Path):
    structured_path = _write_structured(
        scratch_dir / "doc.structured.json",
        {
            "context": {"company": "Missing"},
            "content": {"free_text": "Other text", "fields": {"invoice_number": "MISS-1"}},
        },
    )
    config = ValidatorConfig(
        checks=CheckToggles(free_text=True, context_scalars=False, content_fields=False, rows=False),
    )

    report = DocumentValidator(config).validate(structured_path, _report_path(tmp_report_root, structured_path))

    assert report.result == "PASS"
    assert set(report.checks) == {"free_text"}


def test_validate_does_not_flag_needs_review_when_disabled(scratch_dir: Path, tmp_report_root: Path):
    structured_path = _write_structured(
        scratch_dir / "doc.structured.json",
        {
            "context": {"company": "Missing"},
            "content": {"free_text": "Other text"},
        },
    )
    config = ValidatorConfig(
        checks=CheckToggles(free_text=True, context_scalars=True, content_fields=False, rows=False),
        match=MatchConfig(context_fields=["company"]),
        flag_needs_review=False,
    )

    report = DocumentValidator(config).validate(structured_path, _report_path(tmp_report_root, structured_path))

    assert report.result == "FAIL"
    assert report.needs_review is False
