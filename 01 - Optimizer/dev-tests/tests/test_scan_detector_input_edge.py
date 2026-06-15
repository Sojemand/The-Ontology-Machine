from __future__ import annotations

import pytest

from ingestion_layer_vision.scan_detector import IMAGE_EXTS, is_scan, should_use_vision


def test_is_scan_edge_counts():
    assert is_scan({"metadata": {"page_count": 0}, "blocks": []}, ".pdf") is True
    assert is_scan({"metadata": {"page_count": -5}, "blocks": [{"value": "x" * 200}]}, ".pdf") is False
    blocks = [{"value": "x" * 100} for _ in range(10_000)]
    assert is_scan({"metadata": {"page_count": 1}, "blocks": blocks}, ".pdf") is False


def test_is_scan_non_string_values_and_missing_blocks():
    payload = {"metadata": {"page_count": 1}, "blocks": [{"value": 12345}, {"value": None}, {"value": []}, {"value": {"key": "val"}}]}
    assert isinstance(is_scan(payload, ".pdf"), bool)
    assert is_scan({"metadata": {"page_count": 1}}, ".pdf") is True
    assert isinstance(is_scan({}, ".pdf"), bool)


def test_should_use_vision_edge_cases():
    assert should_use_vision("", is_scan_result=True) is False
    assert should_use_vision(".xyz", is_scan_result=True) is False
    assert should_use_vision(".pdf", is_scan_result=False) is False
    assert should_use_vision(".JPG", is_scan_result=False) is True


@pytest.mark.parametrize("ext", sorted(IMAGE_EXTS))
def test_should_use_vision_all_image_exts(ext: str):
    assert should_use_vision(ext, is_scan_result=False) is True
    assert should_use_vision(ext, is_scan_result=True) is True
