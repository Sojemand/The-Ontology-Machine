from __future__ import annotations

from pathlib import Path

import pytest

from ingestion_layer_file.models import BlockPosition, DataBlock
from ingestion_layer_file.processor import mail_compound_attachment_pages
from ingestion_layer_file.processor.mail_compound_attachments import attachment_pages


def test_image_attachment_pages_emit_ocr_blocks_with_mail_attachment_origin(tmp_path, monkeypatch) -> None:
    rendered_path = tmp_path / "image_attachment_att_1.png"
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"png")

    def fake_render_image_attachment(_source_path, output_path, _processor):
        output_path.write_bytes(b"png")
        return output_path

    def fake_extract_child_vision_blocks(_processor, image_paths):
        assert image_paths == [str(rendered_path)]
        return [
            DataBlock(
                id="child_ocr_1",
                type="paragraph",
                position=BlockPosition(page=1, paragraph_index=0),
                value="recognized attachment text",
                value_type="text",
            )
        ]

    monkeypatch.setattr(mail_compound_attachment_pages, "render_image_attachment", fake_render_image_attachment)
    monkeypatch.setattr(mail_compound_attachment_pages, "extract_child_vision_blocks", fake_extract_child_vision_blocks)

    pages = mail_compound_attachment_pages.image_attachment_pages(
        processor=object(),
        attachment_path=source_path,
        attachment_name="scan.png",
        mail_id="mail_1",
        attachment_id="att_1",
        start_page_number=7,
        temp_root=tmp_path,
    )

    assert len(pages) == 1
    block = pages[0].blocks[0]
    assert block.value == "recognized attachment text"
    assert block.origin == {
        "kind": "mail_attachment",
        "host_page_number": 7,
        "attachment_id": "att_1",
        "attachment_name": "scan.png",
        "child_page_number": 1,
    }
    assert "Image attachment:" not in str(block.value)


def test_attachment_pages_fail_closed_when_attachment_file_is_missing(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="Anhangsdatei fehlt nach Entpacken."):
        attachment_pages(
            processor=object(),
            attachment={"name": "missing.png", "path": "missing.png"},
            bundle_root=tmp_path,
            owner_message={"native_part_key": "mail-part"},
            content_hash="sha256:test",
            mail_id="mail_1",
            start_page_number=3,
            temp_root=tmp_path,
            depth=0,
            render_attachment_assets=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("not reached")),
            build_nested_mail_assets=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("not reached")),
        )
