"""Loader validation, review policy, and rollback tests."""

from __future__ import annotations

import json

import pytest

from tests.fixtures.loader_io import load_input_file


def test_invalid_structured_envelope_returns_error(db, vision_validation_report, make_input_pair):
    invalid_structured = {
        "processing": {"model": "broken", "model_confidence": 0.1},
        "classification": {"document_type": "invoice"},
        "source": {"file_name": "broken.pdf", "file_path": "C:/docs/broken.pdf"},
    }

    result = load_input_file(db, make_input_pair("invalid_envelope", invalid_structured, vision_report=vision_validation_report))

    assert result.status == "error"
    assert "enthaelt keinen Objekt-Block 'content'" in result.reason


def test_invalid_validator_sidecar_object_returns_error(db, vision_structured, tmp_path):
    json_path = tmp_path / "broken_sidecar.structured.json"
    report_path = tmp_path / "broken_sidecar.vision_validation_report.json"
    json_path.write_text(json.dumps(vision_structured, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    result = load_input_file(db, json_path)

    assert result.status == "error"
    assert "kein JSON-Objekt" in result.reason


def test_invalid_normalized_envelope_returns_error(db, vision_structured, vision_validation_report, make_input_pair):
    invalid_normalized = {"classification": {"document_type": "invoice"}, "content": {"fields": {}, "rows": []}}

    result = load_input_file(
        db,
        make_input_pair("invalid_normalized", vision_structured, vision_report=vision_validation_report, normalized=invalid_normalized),
    )

    assert result.status == "error"
    assert "normalized.json" in result.reason
    assert "context" in result.reason


@pytest.mark.parametrize(("explicit_value", "expected"), [("false", 0), ("0", 0), (0, 0), ("", 0), ("true", 1)])
def test_needs_review_parses_scalar_values_robustly(db, vision_structured, vision_validation_report, make_input_pair, explicit_value, expected):
    report = dict(vision_validation_report)
    report["result"] = "pass"
    report["summary"] = {"total_issues": 0}
    report["needs_review"] = explicit_value
    structured = json.loads(json.dumps(vision_structured))
    structured.setdefault("processing", {})["needs_review"] = False
    structured["processing"]["review_reason"] = ""
    json_path = make_input_pair(
        f"needs_review_{str(explicit_value).replace(' ', '_') or 'empty'}",
        structured,
        vision_report=report,
    )

    assert load_input_file(db, json_path).status == "loaded"
    row = db.execute(
        "SELECT needs_review, interpreter_needs_review, normalizer_needs_review FROM documents WHERE id = ?",
        (json_path.stem.replace(".structured", ""),),
    ).fetchone()
    assert row["needs_review"] == expected
    assert row["interpreter_needs_review"] == 0
    assert row["normalizer_needs_review"] == 0


def test_invalid_issue_count_falls_back_to_issue_list(db, vision_structured, vision_validation_report, make_input_pair):
    report = dict(vision_validation_report)
    report.pop("result", None)
    report.pop("needs_review", None)
    report["summary"] = {"total_issues": "abc"}
    report["issues"] = [{"level": "WARN"}, {"level": "WARN"}]

    assert load_input_file(db, make_input_pair("fallback_issues", vision_structured, vision_report=report)).status == "loaded"
    row = db.execute(
        "SELECT validator_issues_count, validator_status, needs_review FROM documents WHERE id = ?",
        ("fallback_issues",),
    ).fetchone()
    assert row["validator_issues_count"] == 2
    assert row["validator_status"] == "warn"
    assert row["needs_review"] == 1


def test_processing_needs_review_survives_validator_pass(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    report = dict(vision_validation_report)
    report["result"] = "pass"
    report["summary"] = {"total_issues": 0}
    report.pop("needs_review", None)
    structured = json.loads(json.dumps(vision_structured))
    structured.setdefault("processing", {})["needs_review"] = False
    structured["processing"]["review_reason"] = ""
    normalized = json.loads(json.dumps(vision_normalized))
    normalized.setdefault("processing", {})["needs_review"] = True
    normalized["processing"]["review_reason"] = "taxonomy_alignment_required"

    json_path = make_input_pair(
        "processing_review_pass",
        structured,
        vision_report=report,
        normalized=normalized,
    )

    assert load_input_file(db, json_path).status == "loaded"
    row = db.execute(
        "SELECT validator_status, validator_issues_count, needs_review, interpreter_needs_review, interpreter_review_reason, normalizer_needs_review, normalizer_review_reason FROM documents WHERE id = ?",
        ("processing_review_pass",),
    ).fetchone()
    assert row["validator_status"] == "pass"
    assert row["validator_issues_count"] == 0
    assert row["needs_review"] == 1
    assert row["interpreter_needs_review"] == 0
    assert row["interpreter_review_reason"] is None
    assert row["normalizer_needs_review"] == 1
    assert row["normalizer_review_reason"] == "taxonomy_alignment_required"


def test_structured_processing_review_survives_normalized_pass(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    report = dict(vision_validation_report)
    report["result"] = "pass"
    report["summary"] = {"total_issues": 0}
    report.pop("needs_review", None)
    structured = json.loads(json.dumps(vision_structured))
    structured.setdefault("processing", {})["needs_review"] = True
    structured["processing"]["review_reason"] = "interpreter_dense_table"

    json_path = make_input_pair(
        "structured_review_pass",
        structured,
        vision_report=report,
        normalized=vision_normalized,
    )

    assert load_input_file(db, json_path).status == "loaded"
    row = db.execute(
        "SELECT validator_status, validator_issues_count, needs_review, interpreter_needs_review, interpreter_review_reason, normalizer_needs_review, normalizer_review_reason FROM documents WHERE id = ?",
        ("structured_review_pass",),
    ).fetchone()
    assert row["validator_status"] == "pass"
    assert row["validator_issues_count"] == 0
    assert row["needs_review"] == 1
    assert row["interpreter_needs_review"] == 1
    assert row["interpreter_review_reason"] == "interpreter_dense_table"
    assert row["normalizer_needs_review"] == 0
    assert row["normalizer_review_reason"] is None


def test_load_document_rolls_back_when_late_insert_fails(db, vision_structured, vision_validation_report, make_input_pair, monkeypatch):
    json_path = make_input_pair("rollback_doc", vision_structured, vision_report=vision_validation_report)
    monkeypatch.setattr(
        "corpus_builder.loader._insert_fts_entry",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = load_input_file(db, json_path)

    assert result.status == "error"
    assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM extracted_fields").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM load_history").fetchone()[0] == 0
