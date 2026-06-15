"""Soft heuristics for Word block and metadata projection."""
from __future__ import annotations


def is_heading_style(style_name: str) -> bool:
    return style_name.strip().lower().startswith("heading")


def heading_titles(paragraphs) -> list[str]:
    return [paragraph.text for paragraph in paragraphs if is_heading_style(paragraph.style_name)]


def formatting_payload(*, bold: bool, font_size: float | None) -> dict[str, float | bool] | None:
    formatting: dict[str, float | bool] = {}
    if bold:
        formatting["bold"] = True
    if font_size is not None:
        formatting["font_size"] = font_size
    return formatting or None


def summarize_headings(headings: list[str], *, max_chars: int = 200) -> str | None:
    if not headings:
        return None
    summary = ", ".join(headings)
    return summary[:max_chars]
