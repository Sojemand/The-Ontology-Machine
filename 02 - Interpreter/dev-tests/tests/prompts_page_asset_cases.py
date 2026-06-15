from __future__ import annotations

import copy

import pytest

from llm_interpreter.prompts import load_page_assets


class TestPageAssets:
    def test_load_page_assets_accepts_valid_request(self, sample_request):
        pages = load_page_assets(sample_request)
        assert len(pages) == 2
        assert pages[0]["page"] == 1

    def test_rejects_non_image_assets(self, sample_request, tmp_path):
        request = copy.deepcopy(sample_request)
        secret = tmp_path / "secret.txt"
        secret.write_text("TOP SECRET", encoding="utf-8")
        request["page_assets"][0]["path"] = str(secret)
        request["page_assets"][0]["media_type"] = "text/plain"

        with pytest.raises(ValueError, match="kein Bild"):
            load_page_assets(request)

    def test_rejects_page_count_mismatch(self, sample_request):
        request = copy.deepcopy(sample_request)
        request["source"]["page_count"] = 3
        with pytest.raises(ValueError, match="page_count"):
            load_page_assets(request)

    def test_accepts_page_scoped_single_image_for_multipage_document(self, sample_request):
        request = copy.deepcopy(sample_request)
        request["source"]["page_count"] = 3
        request["context"]["page_number"] = 2
        request["context"]["document_page_count"] = 3
        request["page_assets"] = [request["page_assets"][1]]

        pages = load_page_assets(request)

        assert len(pages) == 1
        assert pages[0]["page"] == 2

    def test_rejects_out_of_order_pages(self, sample_request):
        request = copy.deepcopy(sample_request)
        request["page_assets"][0]["page"] = 2
        with pytest.raises(ValueError, match="kanonischer Reihenfolge"):
            load_page_assets(request)

    def test_rejects_spoofed_png_with_non_image_bytes(self, sample_request, tmp_path):
        request = copy.deepcopy(sample_request)
        fake_png = tmp_path / "secret.png"
        fake_png.write_text("TOP SECRET", encoding="utf-8")
        request["page_assets"][0]["path"] = str(fake_png)
        request["page_assets"][0]["media_type"] = "image/png"

        with pytest.raises(ValueError, match="kein gueltiges Bild"):
            load_page_assets(request)

    def test_accepts_gif_signature_even_if_declared_generic(self, sample_request, tmp_path):
        request = copy.deepcopy(sample_request)
        gif_path = tmp_path / "page_001.bin"
        gif_path.write_bytes(b"GIF89a\x01\x00\x01\x00")
        request["page_assets"] = [{"page": 1, "path": str(gif_path), "media_type": "application/octet-stream"}]
        request["source"]["page_count"] = 1

        pages = load_page_assets(request)

        assert pages[0]["media_type"] == "image/gif"

    def test_rejects_declared_svg_without_supported_binary_signature(self, sample_request, tmp_path):
        request = copy.deepcopy(sample_request)
        svg_path = tmp_path / "page_001.svg"
        svg_path.write_text("<svg></svg>", encoding="utf-8")
        request["page_assets"] = [{"page": 1, "path": str(svg_path), "media_type": "image/svg+xml"}]
        request["source"]["page_count"] = 1

        with pytest.raises(ValueError, match="kein gueltiges Bild"):
            load_page_assets(request)
