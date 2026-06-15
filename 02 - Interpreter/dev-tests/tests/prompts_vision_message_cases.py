from __future__ import annotations

from pathlib import Path

from llm_interpreter.models import InterpreterConfig
from llm_interpreter.prompts import (
    build_vision_messages,
    describe_page_assets,
    detect_image_media_type,
    resolve_page_media_type,
)


class TestBuildVisionMessages:
    def test_messages_include_high_detail_and_page_order(self, sample_request):
        messages = build_vision_messages(sample_request, InterpreterConfig())
        assert messages[0]["role"] == "system"
        content = messages[1]["content"]
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "input_image"
        assert content[1]["detail"] == "high"
        assert content[2]["type"] == "input_image"
        assert content[1]["page"] == 1
        assert content[2]["page"] == 2

    def test_messages_keep_images_without_prompt_payload_budgeting(self, sample_request):
        page_assets = [
            {
                "page": 1,
                "path": Path("page_001.png"),
                "media_type": "image/png",
                "bytes": b"\x89PNG\r\n\x1a\n" + b"a" * 140000,
            }
        ]

        messages = build_vision_messages(sample_request, InterpreterConfig(), page_assets=page_assets)

        assert [block["type"] for block in messages[1]["content"]] == ["text", "input_image"]

    def test_messages_embed_data_urls(self, sample_request):
        messages = build_vision_messages(sample_request, InterpreterConfig())
        content = messages[1]["content"]
        assert content[1]["image_url"].startswith("data:image/png;base64,")

    def test_declared_non_image_type_falls_back_to_image_guess(self, sample_request):
        page = sample_request["page_assets"][0]
        media_type = resolve_page_media_type(Path(page["path"]), "text/plain")
        assert media_type == "image/png"

    def test_describe_page_assets_is_human_readable(self, sample_request):
        description = describe_page_assets(sample_request)
        assert "Seite 1:" in description
        assert "page_001.png" in description

    def test_detect_image_media_type_recognizes_supported_headers(self):
        assert detect_image_media_type(b"\x89PNG\r\n\x1a\npayload") == "image/png"
        assert detect_image_media_type(b"\xff\xd8\xffpayload") == "image/jpeg"
        assert detect_image_media_type(b"GIF89apayload") == "image/gif"
        assert detect_image_media_type(b"II*\x00payload") == "image/tiff"
        assert detect_image_media_type(b"RIFFxxxxWEBPpayload") == "image/webp"
        assert detect_image_media_type(b"not-an-image") is None
