"""Small page helper functions for the orchestrator stage scheduler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .page_stage_types import PageWorkItem


def required_page_path(path: Path | None, noun: str) -> Path:
    if path is None:
        raise ValueError(f"{noun} is missing.")
    return path


def attach_failure_path(page: PageWorkItem, stage_key: str, path: Path | None) -> None:
    if path is None:
        return
    if stage_key == "request":
        page.request_path = path
    elif stage_key == "interpreter":
        page.structured_path = path
    elif stage_key == "validator":
        page.validation_path = path
    elif stage_key == "normalizer":
        page.normalized_path = path


def record_debug_path(record: Any) -> Path | None:
    path_text = str(getattr(record.artifacts, "interpreter_debug_bundle_path", "") or "").strip()
    return Path(path_text) if path_text else None


def failed_pages_review_reason(pages: list[PageWorkItem]) -> str:
    if len(pages) == 1:
        page = pages[0]
        return f"{page.label} failed after retry budget: {page.last_stage}: {page.last_error}"
    return f"{len(pages)} pages failed after retry budget."
