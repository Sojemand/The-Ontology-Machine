from __future__ import annotations

from ingestion_layer_vision.extractors import markdown_text


class TestMarkdownTextExtractor:
    def test_surface_import_and_selftest(self):
        assert callable(markdown_text.extract)
        assert markdown_text.selftest() == {"status": "ok", "version": "2.0.0"}

    def test_extract_markdown_blocks_and_metadata(self, tmp_path):
        source = tmp_path / "sample.md"
        source.write_text(
            "# Invoice\n\n"
            "Intro paragraph.\n\n"
            "- amount due\n"
            "- currency\n\n"
            "```python\n"
            "print('ok')\n"
            "```\n",
            encoding="utf-8",
        )

        result = markdown_text.extract(source)

        assert result["status"] == "success"
        assert result["needs_ocr"] is False
        assert result["errors"] == []
        assert result["metadata"]["is_markdown"] is True
        assert result["metadata"]["heading_count"] == 1
        assert result["metadata"]["list_item_count"] == 2
        assert result["metadata"]["code_block_count"] == 1
        assert result["metadata"]["headings"] == "Invoice"
        assert [block["type"] for block in result["blocks"]] == [
            "header",
            "paragraph",
            "list_item",
            "list_item",
            "code_block",
        ]
        assert result["blocks"][0]["formatting"]["heading_level"] == 1
        assert result["blocks"][1]["value"] == "Intro paragraph."
        assert result["blocks"][-1]["value"] == "print('ok')"

    def test_extract_config_sections(self, tmp_path):
        source = tmp_path / "settings.ini"
        source.write_text(
            "[core]\nfoo=bar\n\n"
            "[extra]\nbaz=1\n",
            encoding="utf-8",
        )

        result = markdown_text.extract(source)

        assert result["status"] == "success"
        assert result["metadata"]["is_markdown"] is False
        assert result["metadata"]["heading_count"] == 2
        assert result["metadata"]["headings"] == "core, extra"
        assert [block["type"] for block in result["blocks"]] == [
            "header",
            "config_section",
            "header",
            "config_section",
        ]
        assert result["blocks"][1]["value"] == "foo=bar"
        assert result["blocks"][3]["value"] == "baz=1"

    def test_extract_plaintext_paragraphs(self, tmp_path):
        source = tmp_path / "notes.txt"
        source.write_text(
            "First paragraph.\n\nSecond paragraph.\nwith two lines.\n",
            encoding="utf-8",
        )

        result = markdown_text.extract(source)

        assert result["status"] == "success"
        assert result["metadata"]["is_markdown"] is False
        assert result["metadata"]["heading_count"] == 0
        assert [block["value"] for block in result["blocks"]] == [
            "First paragraph.",
            "Second paragraph.\nwith two lines.",
        ]

    def test_missing_file_returns_error_envelope(self, tmp_path):
        result = markdown_text.extract(tmp_path / "missing.md")

        assert result["status"] == "error"
        assert result["blocks"] == []
        assert result["metadata"] == {}
        assert result["needs_ocr"] is False
        assert result["errors"]
