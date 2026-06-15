"""Rendering tests for scan_detector."""
from __future__ import annotations

from pathlib import Path

import pytest

from ingestion_layer_vision.scan_detector import render_page_assets
from ingestion_layer_vision.scan_detector.repository import _cleanup_stage_dir, _create_stage_dir


def test_render_page_assets_paths_and_cleanup(tmp_path):
    pil = pytest.importorskip("PIL.Image")
    source = tmp_path / "single.png"
    output_dir = tmp_path / "output"
    pil.new("RGB", (120, 80), color="white").save(source, "PNG")
    plain_paths = render_page_assets(str(source), str(output_dir))
    keyed_paths = render_page_assets(str(source), str(output_dir), asset_key="same.pdf.deadbeef")
    assert len(plain_paths) == 1
    assert len(keyed_paths) == 1
    assert Path(plain_paths[0]).suffix == ".png"
    assert Path(keyed_paths[0]).parent.name == "same.pdf.deadbeef"


def test_render_pdf_page_assets_use_150_dpi_pixel_grid(tmp_path):
    fitz = pytest.importorskip("fitz")
    pil = pytest.importorskip("PIL.Image")
    source = tmp_path / "one-inch.pdf"
    output_dir = tmp_path / "output"
    doc = fitz.open()
    try:
        page = doc.new_page(width=72, height=72)
        page.insert_text((12, 36), "150 dpi")
        doc.save(source)
    finally:
        doc.close()

    paths = render_page_assets(str(source), str(output_dir))

    assert len(paths) == 1
    with pil.open(paths[0]) as image:
        assert image.size == (150, 150)
        dpi_x, dpi_y = image.info.get("dpi", (0, 0))
        assert abs(dpi_x - 150) < 1
        assert abs(dpi_y - 150) < 1


def test_render_page_assets_sanitizes_and_preserves_siblings(tmp_path):
    pil = pytest.importorskip("PIL.Image")
    source = tmp_path / "single.png"
    output_dir = tmp_path / "output"
    pil.new("RGB", (120, 80), color="white").save(source, "PNG")
    sibling_file = output_dir / "page_assets" / "other-key" / "stale.txt"
    sibling_file.parent.mkdir(parents=True)
    sibling_file.write_text("keep", encoding="utf-8")
    paths = render_page_assets(str(source), str(output_dir), asset_key="../unsafe\\\\name")
    out_path = Path(paths[0])
    assert out_path.parent.parent == output_dir / "page_assets"
    assert out_path.parent.name == "unsafe_name"
    assert sibling_file.exists() is True


def test_render_page_assets_stage_dir_does_not_repeat_long_asset_key(tmp_path):
    long_key = "201611136_V_-_Reinhard_Feinmechanik_Dietzenbach_-_Bestellung_Tieflochbohrungen"
    dest_dir = tmp_path / "page_assets" / long_key

    stage_dir = _create_stage_dir(dest_dir)
    try:
        assert stage_dir.parent == dest_dir.parent
        assert stage_dir.name.startswith(".stage.")
        assert long_key not in stage_dir.name
    finally:
        _cleanup_stage_dir(stage_dir)


def test_render_image_failure_and_missing_pdf_assets_raise(tmp_path, monkeypatch):
    pil = pytest.importorskip("PIL.Image")
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not-an-image")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(pil, "open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("decode failed")))
    with pytest.raises(RuntimeError, match="Keine Vision-Assets erzeugt"):
        render_page_assets(str(broken), str(output_dir))
    pdf_source = tmp_path / "doc.pdf"
    pdf_source.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("ingestion_layer_vision.scan_detector._render_pdf_via_pymupdf", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="Keine Vision-Assets erzeugt"):
        render_page_assets(str(pdf_source), str(output_dir))
