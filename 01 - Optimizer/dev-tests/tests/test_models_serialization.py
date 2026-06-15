from __future__ import annotations

import json

import pytest

from ingestion_layer_vision.models import (
    BlockFormatting,
    BlockPosition,
    DataBlock,
    ExtractionInfo,
    RawExtract,
    SourceInfo,
    raw_extract_to_dict,
    write_raw_extract,
)


class TestSerialization:
    def test_raw_extract_to_dict_uses_minimal_v2_contract(self):
        extract = RawExtract(
            source=SourceInfo(path="/test.pdf", filename="test.pdf", format="pdf", content_hash="sha256:test"),
            extraction=ExtractionInfo(plugin_name="ocr-test", plugin_version="1.0", ocr_used=True),
            metadata={"ocr_backend": "llm", "blank": "", "empty": []},
            blocks=[DataBlock(id="B0", type="paragraph", position=BlockPosition(page=1), value="Header")],
            page_number=1,
            total_pages=1,
        )

        payload = raw_extract_to_dict(extract)

        assert payload["source"]["file_path"] == "/test.pdf"
        assert set(payload.keys()) == {
            "schema_version",
            "optimizer_profile",
            "source",
            "extraction",
            "metadata",
            "context",
            "ocr_reference",
        }
        assert payload["metadata"] == {"ocr_backend": "llm"}
        assert payload["ocr_reference"]["blocks"][0] == {
            "id": "B0",
            "type": "paragraph",
            "value": "Header",
        }

    def test_raw_extract_to_dict_omits_noisy_default_block_fields(self):
        payload = raw_extract_to_dict(
            RawExtract(
                source=SourceInfo(path="/test.pdf", filename="test.pdf", format="pdf", content_hash="sha256:test"),
                blocks=[
                    DataBlock(
                        id="B0",
                        type="paragraph",
                        position=BlockPosition(page=1, paragraph_index=1),
                        value="Plain",
                        formatting=BlockFormatting(bold=False),
                    ),
                    DataBlock(
                        id="B1",
                        type="heading",
                        position=BlockPosition(page=1, paragraph_index=2),
                        value="Bold",
                        formatting=BlockFormatting(bold=True, font_size=18),
                    ),
                ],
            )
        )

        assert payload["ocr_reference"]["blocks"] == [
            {"id": "B0", "type": "paragraph", "value": "Plain"},
            {"id": "B1", "type": "heading", "value": "Bold", "formatting": {"bold": True}},
        ]

    def test_write_raw_extract(self, tmp_path):
        path = tmp_path / "test.pdf.raw.json"
        write_raw_extract(path, RawExtract(source=SourceInfo(filename="test.pdf", format="pdf")))
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "optimizer_raw_v2"
        assert payload["source"]["file_name"] == "test.pdf"
        assert payload["metadata"] == {}
        assert payload["context"] == {}
        assert payload["ocr_reference"] == {"blocks": []}

    def test_raw_extract_to_dict_preserves_blank_ocr_reference_contract(self):
        payload = raw_extract_to_dict(
            RawExtract(
                source=SourceInfo(path="/blank.pdf", filename="blank.pdf", format="pdf"),
                extraction=ExtractionInfo(plugin_name="ocr-test", plugin_version="1.0", ocr_used=True),
                metadata={},
                blocks=[],
                page_number=1,
                total_pages=1,
            )
        )

        assert payload["metadata"] == {}
        assert payload["context"]["page_number"] == 1
        assert payload["ocr_reference"] == {"blocks": []}

    def test_raw_extract_to_dict_rejects_vision_without_image_paths(self):
        extract = RawExtract(needs_llm_vision=True)
        with pytest.raises(ValueError, match="Vision-Extract"):
            raw_extract_to_dict(extract)


class TestRawExtractToDict:
    def test_to_dict_method(self):
        extract = RawExtract(source=SourceInfo(filename="test.xlsx", format="xlsx"))
        assert extract.to_dict()["source"]["file_name"] == "test.xlsx"

    def test_to_dict_equals_function(self):
        extract = RawExtract(
            source=SourceInfo(filename="test.pdf", format="pdf"),
            blocks=[DataBlock(id="B0", type="cell", position=BlockPosition(row=1, col=1), value="value")],
        )
        assert extract.to_dict() == raw_extract_to_dict(extract)

    def test_to_dict_never_serializes_runtime_or_guardrail_shapes(self):
        payload = raw_extract_to_dict(RawExtract(source=SourceInfo(filename="test.pdf", format="pdf")))
        for legacy_key in ("guardrail", "block_refs", "runtime_trace", "compression_audit", "prompt_view", "semantic_policy"):
            assert legacy_key not in payload
