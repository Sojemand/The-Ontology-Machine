"""Core scan-detector tests for scan detection and routing."""
from __future__ import annotations

import pytest

from ingestion_layer_vision.scan_detector import IMAGE_EXTS, is_scan, should_use_vision


class TestIsScan:
    def test_needs_ocr_flag(self):
        assert is_scan({"metadata": {"needs_ocr": True, "page_count": 5}, "blocks": []}, ".pdf") is True

    def test_low_text_density(self):
        assert is_scan({"metadata": {"page_count": 3}, "blocks": [{"value": "short"}]}, ".pdf") is True

    def test_high_text_density_no_scan(self):
        payload = {"metadata": {"page_count": 1, "has_images": False}, "blocks": [{"value": "x" * 500}]}
        assert is_scan(payload, ".pdf") is False

    def test_has_images_flag(self):
        payload = {"metadata": {"page_count": 1, "has_images": True}, "blocks": [{"value": "x" * 500}]}
        assert is_scan(payload, ".pdf") is True

    def test_empty_and_missing_values(self):
        assert is_scan({"metadata": {"page_count": 2}, "blocks": []}, ".pdf") is True
        assert is_scan({"blocks": []}, ".pdf") is True
        payload = {"metadata": {"page_count": 1}, "blocks": [{"value": None}, {"value": ""}, {"value": "x" * 200}]}
        assert is_scan(payload, ".pdf") is False

    def test_multipage_text_density(self):
        assert is_scan({"metadata": {"page_count": 5, "has_images": False}, "blocks": [{"value": "x" * 300}]}, ".pdf") is False
        assert is_scan({"metadata": {"page_count": 10, "has_images": False}, "blocks": [{"value": "x" * 100}]}, ".pdf") is True

    def test_runtime_policy_overrides_scan_threshold_and_image_flag(self):
        payload = {"metadata": {"page_count": 1, "has_images": True}, "blocks": [{"value": "x" * 60}]}
        assert is_scan(payload, ".pdf", min_chars_per_page=80, use_has_images=False) is True
        assert is_scan(payload, ".pdf", min_chars_per_page=40, use_has_images=False) is False


class TestShouldUseVision:
    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"])
    def test_image_formats_always_vision(self, ext):
        assert should_use_vision(ext, is_scan_result=False) is True

    def test_pdf_and_non_image_formats(self):
        assert should_use_vision(".pdf", is_scan_result=True) is True
        assert should_use_vision(".pdf", is_scan_result=False) is False
        for ext in (".xlsx", ".docx", ".msg"):
            assert should_use_vision(ext, is_scan_result=False) is False

    def test_case_insensitive(self):
        assert should_use_vision(".JPG", is_scan_result=False) is True
        assert should_use_vision(".PDF", is_scan_result=True) is True
        assert should_use_vision(".Png", is_scan_result=False) is True

    def test_runtime_policy_overrides_vision_routing(self):
        assert should_use_vision(".jpg", is_scan_result=False, images_always_vision=False) is False
        assert should_use_vision(".pdf", is_scan_result=True, pdf_scans_use_vision=False) is False


class TestImageExts:
    def test_contains_common_formats(self):
        for ext in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}:
            assert ext in IMAGE_EXTS, f"{ext} fehlt in IMAGE_EXTS"

    def test_no_non_image_formats(self):
        for ext in (".pdf", ".xlsx", ".docx", ".msg", ".zip"):
            assert ext not in IMAGE_EXTS
