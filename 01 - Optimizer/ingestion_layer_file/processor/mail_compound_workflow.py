"""Workflow orchestration for flattening mail containers into page assets."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ..models import DataBlock
from ..rendering.repository import cleanup_stage_dir, create_stage_dir
from .mail_compound_attachments import attachment_pages
from .mail_compound_domain import body_blocks, body_render_lines, stable_id, summary_metadata
from .mail_compound_manifest import load_manifest, require_manifest_path
from .mail_compound_rendering import render_text_pages
from .mail_compound_repository import publish_compound_pages
from .mail_compound_types import CompoundPage, MailCompoundAssets
from .mail_thread_splitter import logical_messages


def build_mail_compound_assets(
    processor,
    file_path: Path,
    *,
    fmt: str,
    plugin_result,
    content_hash: str,
    page_images_dir: Path,
    depth_base: int = 0,
    render_attachment_assets,
) -> MailCompoundAssets:
    manifest_path = require_manifest_path(plugin_result.metadata)
    bundle_root = manifest_path.parent
    temp_root = Path(tempfile.mkdtemp(prefix="fom-compound-"))
    stage_dir = create_stage_dir(page_images_dir)
    try:
        manifest = load_manifest(manifest_path)
        messages = logical_messages(manifest, fmt)
        if not messages:
            raise RuntimeError(f"Mail-Container ohne Nachrichten: {file_path.name}")
        pages = _build_pages(
            processor,
            bundle_root=bundle_root,
            logical_messages=messages,
            content_hash=content_hash,
            temp_root=temp_root,
            depth_base=depth_base,
            render_attachment_assets=render_attachment_assets,
        )
        return MailCompoundAssets(
            source_blocks=[block for page in pages for block in page.blocks],
            page_blocks=[block for page in pages for block in page.blocks],
            image_paths=publish_compound_pages(stage_dir, page_images_dir, pages),
            plugin_metadata=summary_metadata(manifest, messages),
        )
    finally:
        cleanup_stage_dir(stage_dir)
        shutil.rmtree(temp_root, ignore_errors=True)
        shutil.rmtree(bundle_root, ignore_errors=True)


def _build_pages(
    processor,
    *,
    bundle_root: Path,
    logical_messages: list[dict[str, object]],
    content_hash: str,
    temp_root: Path,
    depth_base: int,
    render_attachment_assets,
) -> list[CompoundPage]:
    pages: list[CompoundPage] = []

    def build_nested_mail_assets(*args, **kwargs):
        return build_mail_compound_assets(*args, render_attachment_assets=render_attachment_assets, **kwargs)

    for message in logical_messages:
        mail_id = stable_id("mail", content_hash, message["native_part_key"])
        body_page_number = len(pages) + 1
        body_image_paths = render_text_pages(
            lines=body_render_lines(message),
            output_path=temp_root / f"body_{body_page_number:04d}.png",
            processor=processor,
        )
        body_page_numbers = list(range(body_page_number, body_page_number + len(body_image_paths)))
        body_page_blocks = _annotate_body_visual_pages(
            body_blocks(message, page_number=body_page_number, block_prefix=f"{mail_id}__body__"),
            body_page_numbers=body_page_numbers,
        )
        for offset, image_path in enumerate(body_image_paths):
            pages.append(
                CompoundPage(
                    page_number=body_page_number + offset,
                    image_path=image_path,
                    blocks=body_page_blocks if offset == 0 else [],
                )
            )
        for attachment in message.get("attachments", []):
            pages.extend(
                attachment_pages(
                    processor,
                    attachment=attachment,
                    bundle_root=bundle_root,
                    owner_message=message,
                    content_hash=content_hash,
                    mail_id=mail_id,
                    start_page_number=len(pages) + 1,
                    temp_root=temp_root,
                    depth=depth_base + 1,
                    render_attachment_assets=render_attachment_assets,
                    build_nested_mail_assets=build_nested_mail_assets,
                )
            )
    return pages


def _annotate_body_visual_pages(blocks: list[DataBlock], *, body_page_numbers: list[int]) -> list[DataBlock]:
    if len(body_page_numbers) <= 1:
        return blocks
    for block in blocks:
        origin = dict(getattr(block, "origin", None) or {})
        origin.update(
            {
                "kind": "mail_body",
                "visual_page_count": len(body_page_numbers),
                "visual_page_numbers": list(body_page_numbers),
            }
        )
        block.origin = origin
    return blocks
