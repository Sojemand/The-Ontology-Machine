"""Soft heuristics for the odt-odfpy extractor."""
from __future__ import annotations


def coerce_heading_level(raw_level: str | int | None) -> int:
    try:
        return int(raw_level or 1)
    except (TypeError, ValueError):
        return 1


def summarize_headings(headings: list[str], *, max_chars: int = 200) -> str | None:
    if not headings:
        return None
    return ", ".join(headings)[:max_chars]
