"""Stable surface for mail-container flattening in the file processor."""
from __future__ import annotations

from .mail_compound_types import MailCompoundAssets
from .mail_compound_workflow import build_mail_compound_assets as _build_mail_compound_assets
from .single_file_rendering import render_document_assets

__all__ = ["MailCompoundAssets", "build_mail_compound_assets", "render_document_assets"]


def build_mail_compound_assets(
    processor,
    file_path,
    *,
    fmt: str,
    plugin_result,
    content_hash: str,
    page_images_dir,
    depth_base: int = 0,
) -> MailCompoundAssets:
    return _build_mail_compound_assets(
        processor,
        file_path,
        fmt=fmt,
        plugin_result=plugin_result,
        content_hash=content_hash,
        page_images_dir=page_images_dir,
        depth_base=depth_base,
        render_attachment_assets=render_document_assets,
    )
