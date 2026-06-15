"""Types and constants for mail-container flattening."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import DataBlock

MAX_MAIL_DEPTH = 3
MAX_MAIL_PAGE_HEIGHT_PX = 16384
MAX_MAIL_PAGE_BYTES = 15 * 1024 * 1024
MAIL_EXT_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/rtf": ".rtf",
    "application/vnd.ms-outlook": ".msg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "message/rfc822": ".eml",
    "text/html": ".html",
    "text/plain": ".txt",
}


@dataclass
class MailCompoundAssets:
    source_blocks: list[DataBlock]
    page_blocks: list[DataBlock]
    image_paths: list[str]
    plugin_metadata: dict[str, object]


@dataclass
class CompoundPage:
    page_number: int
    image_path: Path
    blocks: list[DataBlock]
