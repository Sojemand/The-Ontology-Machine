from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ingestion_layer_vision.models import ExtractResult, PluginError
from ingestion_layer_vision.processor import adapter


def _processor() -> SimpleNamespace:
    return SimpleNamespace(
        _is_ocr_plugin=lambda name: name == "optimizer-llm-ocr",
        _result_error_detail=lambda result, default: result.errors[0] if result.errors else default,
    )


def test_apply_ocr_route_calls_llm_ocr_for_required_page_assets(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"img")
    calls: list[tuple[list[str], Path]] = []

    def _extract_page_assets(image_paths, *, source_path=None):
        calls.append((list(image_paths), Path(source_path)))
        return {
            "status": "success",
            "blocks": [{"id": "b1", "value": "Hallo", "position": {"page": 1}}],
            "metadata": {"ocr_backend": "llm"},
            "errors": [],
            "processing_time_ms": 7,
            "needs_ocr": False,
        }

    monkeypatch.setattr(adapter, "extract_page_assets", _extract_page_assets)
    original = ExtractResult(status="success", blocks=[], metadata={}, errors=[], processing_time_ms=0, needs_ocr=True)

    result, plugin_name, ocr_was_used = adapter.apply_ocr_route(
        _processor(),
        file_path=tmp_path / "scan.png",
        filename="scan.png",
        ext=".png",
        plugin_name="optimizer-llm-ocr",
        result=original,
        scan_detected=True,
        vision=True,
        image_paths=[str(image_path)],
        requires_ocr=True,
    )

    assert result.status == "success"
    assert result.blocks[0]["value"] == "Hallo"
    assert plugin_name == "optimizer-llm-ocr"
    assert ocr_was_used is True
    assert calls == [([str(image_path)], tmp_path / "scan.png")]


def test_apply_ocr_route_fails_fast_when_required_llm_ocr_has_no_assets(tmp_path: Path) -> None:
    original = ExtractResult(status="success", blocks=[], metadata={}, errors=[], processing_time_ms=0, needs_ocr=True)

    with pytest.raises(PluginError) as exc:
        adapter.apply_ocr_route(
            _processor(),
            file_path=tmp_path / "scan.png",
            filename="scan.png",
            ext=".png",
            plugin_name="optimizer-llm-ocr",
            result=original,
            scan_detected=True,
            vision=True,
            image_paths=[],
            requires_ocr=True,
        )

    assert "keine Page-Assets" in str(exc.value)
