"""Attachment page assembly for flattened mail-container documents."""
from __future__ import annotations

from pathlib import Path

from ..models import DataBlock
from .mail_child_vision import extract_child_vision_blocks
from .mail_compound_domain import rebase_blocks
from .mail_compound_rendering import render_image_attachment
from .mail_compound_types import CompoundPage


def rendered_attachment_pages(
    *,
    image_paths: list[str],
    page_blocks: list[DataBlock],
    attachment_name: str,
    mail_id: str,
    attachment_id: str,
    start_page_number: int,
    block_prefix: str,
) -> list[CompoundPage]:
    total_pages = len(image_paths)
    pages: list[CompoundPage] = []
    for local_page, image_path in enumerate(image_paths, start=1):
        global_page = start_page_number + local_page - 1
        local_blocks = [block for block in page_blocks if int(block.position.page or 1) == local_page]
        rebased_blocks = rebase_blocks(
            local_blocks,
            page_offset=global_page - local_page,
            block_prefix=block_prefix,
        )
        for block in rebased_blocks:
            origin = dict(block.origin or {})
            origin.update(
                {
                    "kind": "mail_attachment",
                    "host_page_number": global_page,
                    "attachment_id": attachment_id,
                    "attachment_name": attachment_name,
                    "child_page_number": local_page,
                }
            )
            block.origin = origin
        pages.append(
            CompoundPage(
                page_number=global_page,
                image_path=Path(image_path),
                blocks=rebased_blocks,
            )
        )
    return pages


def image_attachment_pages(processor, attachment_path: Path, attachment_name: str, mail_id: str, attachment_id: str, start_page_number: int, temp_root: Path) -> list[CompoundPage]:
    image_path = render_image_attachment(
        attachment_path,
        temp_root / f"image_attachment_{attachment_id}.png",
        processor,
    )
    ocr_blocks = extract_child_vision_blocks(processor, [str(image_path)])
    return [
        *rendered_attachment_pages(
            image_paths=[str(image_path)],
            page_blocks=ocr_blocks,
            attachment_name=attachment_name,
            mail_id=mail_id,
            attachment_id=attachment_id,
            start_page_number=start_page_number,
            block_prefix=f"{mail_id}__{attachment_id}__",
        )
    ]
