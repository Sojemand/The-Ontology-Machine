from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ingestion_layer_vision.models import ExtractResult
from ingestion_layer_vision.processor.adapter import render_vision_assets
from ingestion_layer_vision.processor.source_workflow import _extract_source
from ingestion_layer_vision.processor.types import PreparedSource
from ingestion_layer_vision.runtime_policy import ocr_policy
from ingestion_layer_vision.runtime_policy.types import RuntimeOcrPolicy


def _policy(source_mode: str = "release_domain_merge", *, page_image_dpi: int = 360) -> RuntimeOcrPolicy:
    return RuntimeOcrPolicy(
        policy_version="ocr_policy_v1",
        source_mode=source_mode,
        defaults={
            "profile_id": "layout_fidelity_v1",
            "scan": {"min_chars_per_page": 80, "use_has_images": True},
            "vision_route": {"images_always_vision": True, "pdf_scans_use_vision": True},
            "ocr_plugin": {"preferred_plugin": "optimizer-llm-ocr", "force_backup_on_scan": True},
            "render": {"page_image_dpi": page_image_dpi, "page_image_quality": 95, "serializer_quality_mode": "best_quality", "ocr_render_dpi": 450},
        },
    )


def test_page_image_render_policy_forces_interpreter_asset_dpi_to_150() -> None:
    assert ocr_policy.page_image_render_policy(_policy(page_image_dpi=360)) == {"dpi": 150, "quality": 95}


def test_extract_source_records_llm_ocr_need_after_scan_detection(tmp_path) -> None:
    captured: dict[str, object] = {}

    def _detect_scan_state(**kwargs):
        captured["scan_policy"] = kwargs["policy_config"]
        return True

    processor = SimpleNamespace(
        _runtime_policy_state=SimpleNamespace(ocr_policy=_policy()),
        _invoke_plugin=lambda plugin_name, file_path: ExtractResult(status="success", blocks=[], metadata={"page_count": 1, "has_images": True}, errors=[], processing_time_ms=0, needs_ocr=False),
        _detect_scan_state=_detect_scan_state,
    )
    source = PreparedSource(
        entry=SimpleNamespace(path=tmp_path / "invoice.pdf", filename="invoice.pdf", extension=".pdf", relative_path="invoice.pdf", size_bytes=12, content_hash="", created="", modified=""),
        file_path=tmp_path / "invoice.pdf",
        filename="invoice.pdf",
        ext=".pdf",
        fmt="pdf",
        relative_path="invoice.pdf",
        size=12,
        content_hash="sha256:test",
        ingest_id="ing-1",
        plugin_name="pdf-pdfplumber",
    )

    _extract_source(processor, source)

    assert captured["scan_policy"] == {"min_chars_per_page": 80, "use_has_images": True}
    assert source.vision is True
    assert source.ocr_required is False
    assert source.backup_ocr_requested is True
    assert source.render_config == {"dpi": 150, "quality": 95}


def test_render_vision_assets_forwards_runtime_render_profile(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    target = tmp_path / "source.pdf"
    target.write_bytes(b"%PDF-1.7")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    expected = output_dir / "page_assets" / "asset"
    expected.mkdir(parents=True)
    image_path = expected / "page_001.jpg"
    image_path.write_bytes(b"img")

    monkeypatch.setattr(
        "ingestion_layer_vision.processor.render_page_assets",
        lambda file_path, output_dir_text=None, *, asset_key=None, page_assets_dir=None, dpi=300, quality=95: captured.update(
            {"dpi": dpi, "quality": quality, "asset_key": asset_key, "page_assets_dir": page_assets_dir}
        ) or [str(image_path)],
    )

    paths = render_vision_assets(SimpleNamespace(), target, output_dir, "asset", render_config={"dpi": 150, "quality": 95})

    assert paths == [str(image_path)]
    assert captured == {"dpi": 150, "quality": 95, "asset_key": "asset", "page_assets_dir": None}


def test_render_vision_assets_defaults_to_interpreter_asset_dpi(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    target = tmp_path / "source.pdf"
    target.write_bytes(b"%PDF-1.7")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    expected = output_dir / "page_assets" / "asset"
    expected.mkdir(parents=True)
    image_path = expected / "page_001.png"
    image_path.write_bytes(b"img")

    monkeypatch.setattr(
        "ingestion_layer_vision.processor.render_page_assets",
        lambda file_path, output_dir_text=None, *, asset_key=None, page_assets_dir=None, dpi=300, quality=95: captured.update(
            {"dpi": dpi, "quality": quality, "asset_key": asset_key, "page_assets_dir": page_assets_dir}
        ) or [str(image_path)],
    )

    paths = render_vision_assets(SimpleNamespace(), target, output_dir, "asset")

    assert paths == [str(image_path)]
    assert captured == {"dpi": 150, "quality": 95, "asset_key": "asset", "page_assets_dir": None}
