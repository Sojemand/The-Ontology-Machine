from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ingestion_layer_vision.scan_detector import _safe_asset_key, _save_pil_image


def test_safe_asset_key_variants():
    assert _safe_asset_key("!!!@@@###", "fallback.png")
    assert _safe_asset_key("", "test.png")
    assert _safe_asset_key(None, "test.png")
    assert "\\" not in _safe_asset_key("foo\\bar\\baz", "fb.png")


def test_save_pil_image_modes_and_copy_rules():
    rgba = MagicMock()
    rgba.mode = "RGBA"
    converted = MagicMock()
    rgba.convert.return_value = converted
    _save_pil_image(rgba, Path("out.png"), 95, dpi=300)
    rgba.convert.assert_called_once_with("L")
    converted.save.assert_called_once()
    assert converted.save.call_args.kwargs["dpi"] == (300, 300)
    png = MagicMock()
    png.mode = "L"
    _save_pil_image(png, Path("out.png"), 95, dpi=300)
    png.save.assert_called_once()
    assert png.save.call_args[0][1] == "PNG"
    assert png.save.call_args.kwargs["dpi"] == (300, 300)
