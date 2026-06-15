from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator_vision.models.structured_io import read_json_object
from validator_vision.models.types import StructuredDocument
from validator_vision.validator import adapter as validator_adapter
from validator_vision.validator.raw_index import resolve_raw_path

from file_profile_fixtures import file_structured, write_json


def test_read_json_object_rejects_oversized_inputs(monkeypatch, scratch_dir: Path):
    payload_path = scratch_dir / "large.json"
    payload_path.write_text(json.dumps({"payload": "x" * 64}), encoding="utf-8")
    monkeypatch.setattr("validator_vision.models.structured_io.MAX_JSON_BYTES", 16)

    with pytest.raises(ValueError, match="zu gross"):
        read_json_object(payload_path, label="Structured JSON")


def test_batch_discovery_rejects_too_many_structured_documents(monkeypatch, scratch_dir: Path):
    structured_root = scratch_dir / "structured"
    structured_root.mkdir()
    for index in range(3):
        (structured_root / f"doc_{index}.structured.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(validator_adapter, "MAX_BATCH_DOCUMENTS", 2)

    with pytest.raises(ValueError, match="Zu viele Structured-Dokumente"):
        validator_adapter.discover_structured_documents(structured_root)


def test_raw_index_reports_skipped_unreadable_raw_files(scratch_dir: Path):
    raw_root = scratch_dir / "raw"
    raw_root.mkdir()
    (raw_root / "broken.raw.json").write_text("[", encoding="utf-8")
    document = file_structured(
        content_hash="sha256:missing",
        fields={},
        rows=[],
        free_text="",
    )

    write_json(scratch_dir / "doc.structured.json", document)
    with pytest.raises(ValueError, match="Uebersprungene Raw-Dateien: 1"):
        resolve_raw_path(StructuredDocument.from_dict(document), raw_root=raw_root)
