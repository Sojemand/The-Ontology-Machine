from __future__ import annotations

import json
from pathlib import Path

import pytest

from normalizer_vision.document_io import (
    DocumentIoValidationError,
    StructuredDocument,
    budget_normalized_output_file_name,
    load_structured_document,
    normalized_output_file_name,
    validate_structured_envelope,
)


def test_validate_structured_envelope_rejects_missing_required_keys():
    with pytest.raises(DocumentIoValidationError, match="processing"):
        validate_structured_envelope({"schema_version": "1.0"})


def test_validate_structured_envelope_rejects_non_object_sections():
    with pytest.raises(DocumentIoValidationError, match="classification"):
        validate_structured_envelope(
            {
                "schema_version": "1.0",
                "processing": {},
                "classification": [],
                "context": {},
                "content": {},
            }
        )


def test_load_structured_document_rejects_non_object_root(tmp_path):
    structured_path = tmp_path / "doc.structured.json"
    structured_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON root muss ein Objekt sein"):
        load_structured_document(structured_path)


def test_load_structured_document_returns_boundary_type(tmp_path):
    structured_path = tmp_path / "doc.structured.json"
    payload = {
        "schema_version": "1.0",
        "processing": {},
        "classification": {},
        "context": {},
        "content": {},
    }
    structured_path.write_text(json.dumps(payload), encoding="utf-8")

    document = load_structured_document(structured_path)

    assert isinstance(document, StructuredDocument)
    assert document.path == structured_path
    assert document.payload == payload


def test_load_structured_document_rejects_files_above_size_limit(tmp_path):
    structured_path = tmp_path / "doc.structured.json"
    payload = {
        "schema_version": "1.0",
        "processing": {},
        "classification": {},
        "context": {},
        "content": {},
    }
    structured_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DocumentIoValidationError, match="max_structured_bytes"):
        load_structured_document(structured_path, max_bytes=16)


def test_normalized_output_file_name_rewrites_structured_suffix():
    assert normalized_output_file_name(Path("nested/doc.structured.json")) == "doc.structured.normalized.json"


def test_normalized_output_file_name_appends_fallback_suffix_for_nonstandard_names():
    assert normalized_output_file_name(Path("invoice.json")) == "invoice.json.normalized.json"


def test_budget_normalized_output_file_name_shortens_overlong_windows_path():
    parent = Path("C:/workspace/output/session/outputs") / ("segment_" + "x" * 60)
    structured_path = Path(("invoice_" + "z" * 180) + ".structured.json")

    name = budget_normalized_output_file_name(parent, structured_path)

    assert len(str(parent / name)) <= 259
    assert name.endswith(".structured.normalized.json")
    assert "z" * 120 not in name


def test_budget_normalized_output_file_name_fails_when_parent_is_too_deep():
    parent = Path("C:/") / ("x" * 230)

    with pytest.raises(ValueError, match="Windows-Pfadbudget"):
        budget_normalized_output_file_name(parent, Path("doc.structured.json"))
