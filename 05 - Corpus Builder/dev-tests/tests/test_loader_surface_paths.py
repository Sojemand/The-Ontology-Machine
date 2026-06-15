"""Loader surface, sidecar, and path handling tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from corpus_builder.loader import detect_field_type, load_from_file as _load_from_file
from tests.fixtures.loader_io import load_input_file


def test_loader_surface_exports_path_stable_entry_points():
    from corpus_builder.loader import detect_field_type as imported_detect_field_type, load_from_file, rematerialize_document

    assert imported_detect_field_type is detect_field_type
    assert callable(load_from_file)
    assert callable(rematerialize_document)


def test_core_load_from_file_requires_explicit_validation_path(db, vision_structured, vision_validation_report, make_input_pair):
    json_path = make_input_pair("explicit_bundle", vision_structured, vision_report=vision_validation_report)

    with pytest.raises(TypeError):
        _load_from_file(db, json_path)


def test_missing_sidecar_fails(db, vision_structured, make_input_pair):
    json_path = make_input_pair("missing_report", vision_structured)

    result = load_input_file(db, json_path)

    assert result.status == "error"
    assert "vision_validation_report.json" in result.reason
    assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_sidecar_can_be_resolved_from_sibling_validator_output(
    db,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    tmp_path,
):
    interpreter_dir = tmp_path / "Interpreter Output"
    validator_dir = tmp_path / "Validator Output"
    interpreter_dir.mkdir()
    validator_dir.mkdir()
    json_path = interpreter_dir / "sibling_doc.structured.json"
    normalized_path = interpreter_dir / "sibling_doc.structured.normalized.json"
    json_path.write_text(json.dumps(vision_structured, indent=2, ensure_ascii=False), encoding="utf-8")
    normalized_path.write_text(json.dumps(vision_normalized, indent=2, ensure_ascii=False), encoding="utf-8")
    (validator_dir / "sibling_doc.vision_validation_report.json").write_text(
        json.dumps(vision_validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result = load_input_file(db, json_path, validation_path=validator_dir / "sibling_doc.vision_validation_report.json")

    assert result.status == "loaded"


def test_both_sidecars_prefer_vision(db, vision_structured, vision_validation_report, legacy_validation_report, make_input_pair):
    vision_report = dict(vision_validation_report)
    vision_report["result"] = "warn"
    legacy_report = dict(legacy_validation_report)
    legacy_report["result"] = "fail"
    json_path = make_input_pair("sidecar_preference", vision_structured, vision_report=vision_report, legacy_report=legacy_report)

    result = load_input_file(db, json_path)

    assert result.status == "loaded"
    row = db.execute("SELECT validator_status FROM documents WHERE id = ?", ("sidecar_preference",)).fetchone()
    assert row["validator_status"] == "warn"


def test_normalized_source_path_beats_structured_source_path(db, vision_structured, vision_validation_report, vision_normalized, make_input_pair):
    normalized = dict(vision_normalized)
    normalized["source"] = {"file_name": "normalized.pdf", "file_path": "C:/normalized/doc.pdf"}
    json_path = make_input_pair(
        "normalized_source",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=normalized,
    )
    result = load_input_file(db, json_path)

    assert result.status == "loaded"
    row = db.execute("SELECT file_path FROM documents WHERE id = ?", ("normalized_source",)).fetchone()
    assert row["file_path"] == "C:/normalized/doc.pdf"


def test_missing_payload_source_falls_back_to_normalized_artifact_path(db, vision_structured, vision_validation_report, vision_normalized, make_input_pair):
    structured = dict(vision_structured)
    structured["source"] = {}
    normalized = dict(vision_normalized)
    normalized["source"] = {}
    json_path = make_input_pair(
        "artifact_fallback",
        structured,
        vision_report=vision_validation_report,
        normalized=normalized,
    )
    result = load_input_file(db, json_path)

    assert result.status == "loaded"
    row = db.execute("SELECT file_path FROM documents WHERE id = ?", ("artifact_fallback",)).fetchone()
    assert row["file_path"] == str(json_path.with_name("artifact_fallback.structured.normalized.json"))


def test_missing_payload_source_keeps_structured_source_path(db, vision_structured, vision_validation_report, make_input_pair):
    json_path = make_input_pair("no_img_dir", vision_structured, vision_report=vision_validation_report)
    result = load_input_file(db, json_path)

    assert result.status == "loaded"
    row = db.execute("SELECT file_path FROM documents WHERE id = ?", ("no_img_dir",)).fetchone()
    assert row["file_path"] == "C:/docs/2026-03-13 17-33.pdf"


def test_detect_field_type_handles_mixed_locale_and_negative_currency():
    assert detect_field_type("amount", "1,234.56") == ("number", 1234.56)
    assert detect_field_type("amount", "1.234,56") == ("number", 1234.56)
    assert detect_field_type("amount", "EUR 12,34") == ("currency", 12.34)
    assert detect_field_type("amount", "-12,34 EUR") == ("currency", -12.34)
    assert detect_field_type("amount", "(1.234,56 EUR)") == ("currency", -1234.56)
    assert detect_field_type("amount", "1.234") == ("text", None)
