from __future__ import annotations

from ingestion_layer_vision.models import (
    BlockFormatting,
    BlockPosition,
    DataBlock,
    ExtractionInfo,
    IngestionReport,
    OutputFilters,
    PluginManifest,
    RawExtract,
    SourceInfo,
)


class TestDataclasses:
    def test_defaults(self):
        assert OutputFilters().format is None
        assert OutputFilters().batch_size == 0
        report = IngestionReport()
        assert report.successful == 0
        assert report.failed == 0
        assert report.vision_docs == 0
        assert report.text_docs == 0
        assert report.total_images_rendered == 0
        manifest = PluginManifest()
        assert manifest.formats == []
        assert manifest.priority == 0
        extract = RawExtract()
        assert extract.needs_llm_vision is False
        assert extract.image_paths == []
        assert extract.metadata == {}
        assert extract.blocks == []
        assert extract.is_scan is False
        assert extract.page_number is None
        assert extract.total_pages is None
        assert ExtractionInfo().ocr_used is False
        assert SourceInfo().relative_path == ""

    def test_minimal_raw_v2_preserves_blocks_without_semantic_shapes(self):
        extract = RawExtract(
            source=SourceInfo(
                ingest_id="ingest-123",
                path="/docs/scan.pdf",
                filename="scan.pdf",
                file_ext=".pdf",
                format="pdf",
                content_hash="sha256:test",
                relative_path="docs/scan.pdf",
            ),
            extraction=ExtractionInfo(plugin_name="ocr-test", plugin_version="1.0", ocr_used=True),
            metadata={"ocr_quality_mode": "best_quality", "empty": "", "nested": {"drop": None}},
            needs_llm_vision=True,
            image_paths=["/work/page_assets/scan/page_001.png"],
            blocks=[
                DataBlock(
                    id="page1_para_0",
                    type="paragraph",
                    layout_label="header",
                    position=BlockPosition(page=1, paragraph_index=0),
                    value="Rechnung",
                    value_type="text",
                    formatting=BlockFormatting(bold=True),
                    confidence=0.98,
                ),
                DataBlock(
                    id="empty",
                    type="paragraph",
                    position=BlockPosition(page=1, paragraph_index=1),
                    value="",
                ),
            ],
            is_scan=True,
            page_number=1,
            total_pages=1,
        )

        payload = extract.to_dict()

        assert payload["schema_version"] == "optimizer_raw_v2"
        assert set(payload) == {"schema_version", "optimizer_profile", "source", "extraction", "metadata", "context", "ocr_reference"}
        assert payload["source"]["file_name"] == "scan.pdf"
        assert payload["source"]["is_scan"] is True
        assert payload["metadata"] == {"ocr_quality_mode": "best_quality"}
        assert payload["context"] == {
            "page_number": 1,
            "document_page_count": 1,
            "source_document_path": "docs/scan.pdf",
            "page_source_path": "docs/scan.pdf::page=001-of-001",
        }
        assert payload["ocr_reference"]["blocks"] == [
            {
                "id": "page1_para_0",
                "type": "paragraph",
                "layout_label": "header",
                "value": "Rechnung",
                "confidence": 0.98,
                "formatting": {"bold": True},
            }
        ]
        for legacy_key in ("doc", "ctx", "vision_assets", "guardrail", "block_refs", "runtime_trace", "compression_audit"):
            assert legacy_key not in payload
