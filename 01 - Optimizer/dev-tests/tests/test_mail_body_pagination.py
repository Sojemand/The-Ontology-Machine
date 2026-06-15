from __future__ import annotations

from PIL import Image
import pytest

from ingestion_layer_file.processor import mail_compound_rendering, mail_compound_workflow
from ingestion_layer_file.processor.mail_compound_rendering import render_text_page, render_text_pages


class _Config:
    render_width_px = 420
    render_height_px = 900
    default_font_size_pt = 10
    heading_font_size_pt = 12


class _Processor:
    _config = _Config()


def test_long_mail_body_is_rendered_as_bounded_visual_pages(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mail_compound_rendering, "MAX_MAIL_PAGE_HEIGHT_PX", 520)
    lines = [
        "From: sender@example.test",
        "To: reader@example.test",
        "Subject: Long note",
        "",
        *[f"Mail body line {index:03d} with enough text to wrap in the rendered evidence image." for index in range(80)],
    ]

    with pytest.raises(RuntimeError, match="ein einzelnes PNG"):
        render_text_page(lines=lines, output_path=tmp_path / "single.png", processor=_Processor())

    page_paths = render_text_pages(lines=lines, output_path=tmp_path / "body.png", processor=_Processor())

    assert len(page_paths) > 1
    assert page_paths[0].name == "body.png"
    assert page_paths[1].name == "body_part0002.png"
    for page_path in page_paths:
        assert page_path.exists()
        with Image.open(page_path) as image:
            assert image.height <= 520


def test_mail_workflow_keeps_body_blocks_on_first_visual_slice(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mail_compound_rendering, "MAX_MAIL_PAGE_HEIGHT_PX", 520)
    message = {
        "native_part_key": "root-message",
        "headers": {
            "from": "sender@example.test",
            "to": "reader@example.test",
            "subject": "Long note",
            "date": "Tue, 02 Jun 2026 12:00:00 +0000",
        },
        "body_text": "\n".join(
            f"Mail body line {index:03d} with enough text to wrap in the rendered evidence image."
            for index in range(80)
        ),
        "attachments": [],
    }

    pages = mail_compound_workflow._build_pages(
        _Processor(),
        bundle_root=tmp_path,
        logical_messages=[message],
        content_hash="sha256:test",
        temp_root=tmp_path,
        depth_base=0,
        render_attachment_assets=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("not reached")),
    )

    assert len(pages) > 1
    assert pages[0].blocks
    assert all(not page.blocks for page in pages[1:])
    body_origin = pages[0].blocks[-1].origin
    assert body_origin == {
        "kind": "mail_body",
        "visual_page_count": len(pages),
        "visual_page_numbers": [page.page_number for page in pages],
    }
