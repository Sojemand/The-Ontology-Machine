"""Stable processor surface for the Optimizer."""
from __future__ import annotations

from ..models import atomic_json_write, raw_extract_to_dict
from ..rendering import render_non_pdf_document, render_pdf_to_images
from ..scan_detector import is_scan, render_page_images, should_use_vision
from .claims_repository import _OUTPUT_CLAIM_SUFFIX, _RUN_LOCK_NAME, _RUNS_DIR_NAME
from .policy import _MAX_ASSET_KEY_LENGTH, _MAX_OUTPUT_SLUG_LENGTH, _MAX_OUTPUT_WRITE_ATTEMPTS, _OUTPUT_SAFE_CHAR_RE
from .single_file_rendering import render_document_assets
from .surface import Processor

__all__ = [
    "Processor",
    "_MAX_ASSET_KEY_LENGTH",
    "_MAX_OUTPUT_SLUG_LENGTH",
    "_MAX_OUTPUT_WRITE_ATTEMPTS",
    "_OUTPUT_CLAIM_SUFFIX",
    "_OUTPUT_SAFE_CHAR_RE",
    "_RUN_LOCK_NAME",
    "_RUNS_DIR_NAME",
    "atomic_json_write",
    "is_scan",
    "raw_extract_to_dict",
    "render_document_assets",
    "render_non_pdf_document",
    "render_page_images",
    "render_pdf_to_images",
    "should_use_vision",
]
