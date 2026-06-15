"""Attachment expansion for flattened mail-container documents."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..models import DataBlock, FileFormat
from .mail_child_vision import extract_child_vision_blocks
from .mail_compound_attachment_pages import image_attachment_pages, rendered_attachment_pages
from .mail_compound_domain import rebase_blocks, stable_id
from .mail_compound_types import CompoundPage, MAIL_EXT_BY_CONTENT_TYPE, MAX_MAIL_DEPTH


def attachment_pages(
    processor,
    *,
    attachment: dict[str, Any],
    bundle_root: Path,
    owner_message: dict[str, Any],
    content_hash: str,
    mail_id: str,
    start_page_number: int,
    temp_root: Path,
    depth: int,
    render_attachment_assets: Callable[..., tuple[list[str], list[DataBlock], str, str]],
    build_nested_mail_assets: Callable[..., Any],
) -> list[CompoundPage]:
    attachment_name = str(attachment.get("name", "") or "").strip() or "attachment"
    attachment_id = stable_id(
        "att",
        content_hash,
        owner_message.get("native_part_key", ""),
        attachment.get("native_part_key", ""),
        attachment_name,
    )
    if depth > MAX_MAIL_DEPTH:
        raise RuntimeError("Verschachtelungstiefe fuer Mail-Anhang ueberschritten.")
    attachment_path = bundle_root / str(attachment.get("path", "") or "")
    if not attachment_path.exists() or not attachment_path.is_file():
        raise RuntimeError("Anhangsdatei fehlt nach Entpacken.")
    attachment_path = _ensure_extension(attachment_path, attachment)
    fmt = FileFormat.from_ext(attachment_path.suffix.lower())
    if fmt == FileFormat.UNKNOWN:
        raise ValueError(f"Nicht unterstuetzter Anhang: {attachment_path.suffix.lower() or attachment_name}")
    if FileFormat.is_mail_format(fmt):
        pages = _nested_mail_pages(
            processor,
            attachment_path=attachment_path,
            fmt=fmt,
            content_hash=content_hash,
            outer_mail_id=mail_id,
            outer_attachment_id=attachment_id,
            outer_attachment_name=attachment_name,
            start_page_number=start_page_number,
            temp_root=temp_root,
            depth=depth + 1,
            build_nested_mail_assets=build_nested_mail_assets,
        )
        if pages:
            return pages
    if fmt == FileFormat.IMAGE:
        return image_attachment_pages(
            processor,
            attachment_path,
            attachment_name,
            mail_id,
            attachment_id,
            start_page_number,
            temp_root,
        )

    plugin_name = processor._plugin_mgr.get_plugin_for_format(attachment_path.suffix.lower())
    if not plugin_name:
        raise ValueError(f"Kein Plugin fuer Anhangsformat: {attachment_path.suffix.lower()}")
    result = processor._plugin_mgr.invoke(plugin_name, attachment_path)
    if getattr(result, "status", "") != "success":
        detail = "; ".join(str(item).strip() for item in getattr(result, "errors", []) if str(item).strip())
        raise RuntimeError(detail or f"Plugin {plugin_name} lieferte Fehler fuer {attachment_name}")
    if getattr(result, "needs_ocr", False) and fmt != FileFormat.PDF:
        raise RuntimeError(f"Anhang verlangt OCR ohne konfiguriertes OCR-Plugin: {attachment_name}")

    source_blocks = processor._parse_blocks(result.blocks)
    image_paths, page_blocks, _route, _source = render_attachment_assets(
        processor,
        attachment_path,
        fmt=fmt,
        source_blocks=source_blocks,
        page_images_dir=temp_root / f"attachment_pages_{attachment_id}",
    )
    if getattr(result, "needs_ocr", False):
        page_blocks = extract_child_vision_blocks(processor, image_paths)
    if not image_paths:
        raise RuntimeError(f"Vision-Assets fehlen fuer Anhang {attachment_name}")
    return rendered_attachment_pages(
        image_paths=image_paths,
        page_blocks=page_blocks,
        attachment_name=attachment_name,
        mail_id=mail_id,
        attachment_id=attachment_id,
        start_page_number=start_page_number,
        block_prefix=f"{mail_id}__{attachment_id}__",
    )


def _ensure_extension(attachment_path: Path, attachment: dict[str, Any]) -> Path:
    if attachment_path.suffix:
        return attachment_path
    ext = MAIL_EXT_BY_CONTENT_TYPE.get(str(attachment.get("content_type", "")).strip().lower(), "")
    if not ext:
        return attachment_path
    renamed = attachment_path.with_name(f"{attachment_path.name}{ext}")
    attachment_path.rename(renamed)
    return renamed


def _nested_mail_pages(
    processor,
    *,
    attachment_path: Path,
    fmt: str,
    content_hash: str,
    outer_mail_id: str,
    outer_attachment_id: str,
    outer_attachment_name: str,
    start_page_number: int,
    temp_root: Path,
    depth: int,
    build_nested_mail_assets: Callable[..., Any],
) -> list[CompoundPage]:
    plugin_name = processor._plugin_mgr.get_plugin_for_format(attachment_path.suffix.lower())
    if not plugin_name:
        return []
    result = processor._plugin_mgr.invoke(plugin_name, attachment_path)
    if getattr(result, "status", "") != "success":
        detail = "; ".join(str(item).strip() for item in getattr(result, "errors", []) if str(item).strip())
        raise RuntimeError(detail or f"Mail-Anhang konnte nicht verarbeitet werden: {outer_attachment_name}")
    nested_assets = build_nested_mail_assets(
        processor,
        attachment_path,
        fmt=fmt,
        plugin_result=result,
        content_hash=content_hash,
        page_images_dir=temp_root / f"nested_mail_{outer_attachment_id}",
        depth_base=depth,
    )
    pages: list[CompoundPage] = []
    for index, image_path in enumerate(nested_assets.image_paths, start=1):
        page_number = start_page_number + index - 1
        page_blocks = [
            block for block in nested_assets.page_blocks if int(block.position.page or 1) == index
        ]
        pages.append(
            CompoundPage(
                page_number=page_number,
                image_path=Path(image_path),
                blocks=rebase_blocks(
                    page_blocks,
                    page_offset=page_number - index,
                    block_prefix=f"{outer_mail_id}__{outer_attachment_id}__nested__",
                ),
            )
        )
    return pages
