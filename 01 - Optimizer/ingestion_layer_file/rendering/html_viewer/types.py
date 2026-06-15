"""Typed contracts for the HTML viewer workflow."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

TEXT_VIEWER_EXTS = {
    ".txt",
    ".md",
    ".markdown",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".properties",
}
MARKDOWN_EXTS = {".md", ".markdown"}
CONFIG_EXTS = {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties"}
A4_WIDTH_PT = 595.2755905511812
A4_HEIGHT_PT = 841.8897637795277


class DocumentKind(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    CONFIG = "config"


@dataclass(frozen=True)
class ViewerSource:
    path: Path
    ext: str
    name: str
    text: str


@dataclass(frozen=True)
class ViewerLayout:
    page_margin_pt: float
    default_font_size_pt: float
    code_font_size_pt: float
    heading_font_size_pt: float
    page_width_pt: float = A4_WIDTH_PT
    page_height_pt: float = A4_HEIGHT_PT


@dataclass(frozen=True)
class ViewerHtmlDocument:
    kind: DocumentKind
    title: str
    body_html: str
    html_payload: str


class HtmlViewerStageError(RuntimeError):
    """Stage-labelled HTML viewer failure."""

    def __init__(self, stage: str, detail: str) -> None:
        self.stage = stage
        self.detail = detail.strip() or "unknown error"
        super().__init__(f"{stage}: {self.detail}")
