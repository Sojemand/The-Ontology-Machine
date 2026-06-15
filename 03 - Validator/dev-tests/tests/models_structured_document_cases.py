from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator_vision.models import PreparedFreeText, StructuredDocument


def test_structured_document_boundary_handles_non_string_free_text(scratch_dir: Path):
    structured_path = scratch_dir / "doc.structured.json"
    structured_path.write_text(
        json.dumps(
            {
                "processing": {"interpreter_profile": "vision"},
                "content": {"free_text": 42, "rows": [None, {"position": "Item"}]},
            }
        ),
        encoding="utf-8",
    )
    document = StructuredDocument.from_path(structured_path)
    assert document.free_text == PreparedFreeText.from_value(42)
    assert document.free_text.is_present is False
    assert [row.index for row in document.rows] == [1]
    assert document.file_name == "doc"
    assert document.content_hash.startswith("sha256:")


@pytest.mark.parametrize("section", ["context", "content", "source", "processing"])
def test_structured_document_rejects_non_object_sections(section: str):
    payload = {"processing": {"interpreter_profile": "vision"}}
    payload[section] = ["broken"]

    with pytest.raises(ValueError, match=f"{section} muss ein JSON-Objekt sein"):
        StructuredDocument.from_dict(payload)


@pytest.mark.parametrize(
    ("content", "match"),
    [
        ({"fields": ["broken"]}, "content.fields muss ein JSON-Objekt sein"),
        ({"rows": {"broken": True}}, "content.rows muss eine Liste sein"),
    ],
)
def test_structured_document_rejects_invalid_content_shapes(content: dict, match: str):
    with pytest.raises(ValueError, match=match):
        StructuredDocument.from_dict(
            {
                "processing": {"interpreter_profile": "vision"},
                "content": content,
            }
        )


def test_structured_document_requires_interpreter_profile():
    with pytest.raises(ValueError, match="processing.interpreter_profile"):
        StructuredDocument.from_dict({"content": {"free_text": "hello"}})
