from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingestion_layer_vision.scan_detector import render_page_assets


def test_render_unsupported_format_returns_empty(tmp_path: Path):
    dummy = tmp_path / "file.docx"
    dummy.write_bytes(b"\x00" * 64)
    assert render_page_assets(str(dummy), str(tmp_path)) == []


def test_render_dest_dir_creation_failure(tmp_path: Path):
    dummy = tmp_path / "file.pdf"
    dummy.write_bytes(b"%PDF-1.4 fake")
    with patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            render_page_assets(str(dummy), str(tmp_path))


def test_render_pdf_failures_leave_clean_directory(tmp_path: Path):
    dummy = tmp_path / "file.pdf"
    dummy.write_bytes(b"%PDF-1.4 fake")
    with patch("ingestion_layer_vision.scan_detector._render_pdf_via_pymupdf", return_value=None):
        with pytest.raises(RuntimeError, match="Keine Vision-Assets erzeugt"):
            render_page_assets(str(dummy), str(tmp_path))
    page_assets_root = tmp_path / "page_assets"
    assert page_assets_root.exists()
    assert list(page_assets_root.iterdir()) == []


def test_render_image_multiframe_tiff(tmp_path: Path):
    dummy = tmp_path / "multi.tif"
    dummy.write_bytes(b"\x00" * 64)
    mock_frame = MagicMock()
    mock_frame.mode = "RGB"
    mock_frame.copy.return_value = mock_frame
    mock_frame.convert.return_value = mock_frame
    mock_frame.getcolors.return_value = [(1, (0, 0, 0))] * 200
    mock_frame.thumbnail = MagicMock()
    mock_frame.save = MagicMock(side_effect=lambda path, *args, **kwargs: Path(path).write_bytes(b"frame"))
    mock_image = MagicMock()
    mock_image.__enter__ = MagicMock(return_value=mock_image)
    mock_image.__exit__ = MagicMock(return_value=False)
    mock_image.n_frames = 3
    mock_image.seek = MagicMock()
    mock_image.copy.return_value = mock_frame
    mock_image.mode = "RGB"
    with patch("PIL.Image.open", return_value=mock_image):
        result = render_page_assets(str(dummy), str(tmp_path))
    assert len(result) == 3
    assert mock_image.seek.call_count == 3
    assert all(Path(path).is_file() for path in result)


def test_render_concurrent_same_asset_key_is_stable(tmp_path: Path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    dummy = case_dir / "photo.jpg"
    dummy.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)
    barrier = threading.Barrier(2, timeout=5)
    errors: list[Exception] = []
    results: list[list[str]] = [[], []]
    mock_frame = MagicMock()
    mock_frame.mode = "RGB"
    mock_frame.copy.return_value = mock_frame
    mock_frame.convert.return_value = mock_frame
    mock_frame.getcolors.return_value = [(1, (0, 0, 0))] * 200
    mock_frame.thumbnail = MagicMock()
    mock_frame.save = MagicMock(side_effect=lambda path, *args, **kwargs: Path(path).write_bytes(b"frame"))
    mock_image = MagicMock()
    mock_image.__enter__ = MagicMock(return_value=mock_image)
    mock_image.__exit__ = MagicMock(return_value=False)
    mock_image.n_frames = 1
    mock_image.copy.return_value = mock_frame
    mock_image.mode = "RGB"

    def delayed_open(*args, **kwargs):
        barrier.wait()
        return mock_image

    def worker(index: int):
        try:
            results[index] = render_page_assets(str(dummy), str(case_dir), asset_key="shared_key")
        except Exception as exc:
            errors.append(exc)

    with patch("PIL.Image.open", side_effect=delayed_open):
        dest = case_dir / "page_assets" / "shared_key"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "stale.txt").write_text("stale", encoding="utf-8")
        threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
    final_file = case_dir / "page_assets" / "shared_key" / "page_001.png"
    assert errors == []
    assert final_file.is_file()
    assert not (case_dir / "page_assets" / "shared_key" / "stale.txt").exists()
    assert all(len(result) == 1 for result in results)
    assert all(Path(result[0]).samefile(final_file) for result in results)
