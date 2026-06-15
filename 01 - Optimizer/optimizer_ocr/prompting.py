"""Prompt loading and provider content construction for Optimizer OCR."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


PROMPT_FILE_NAME = "optimizer_ocr_prompt.md"
DEFAULT_OCR_PROMPT_TEMPLATE = (
    "Extract OCR text from the provided rendered document page images.\n"
    "Return only one valid JSON object and no markdown.\n"
    "The JSON object must contain a top-level 'blocks' array.\n"
    "The request contains {page_count} rendered page image(s).\n"
    "Each block must contain only id, type, and value.\n"
    "Use type='paragraph' unless a visible heading or table cell is clearer.\n"
    "Add layout_label only when it is useful for visible layout (header, footer, address, totals, table_header, table_body).\n"
    "Do not output position objects, row/column coordinates, value_type='text', nulls, empty objects, or empty arrays.\n"
    "For multi-page input, add a top-level page number only when the block is not on page 1.\n"
    "Add formatting only as {\"bold\":true} when the text is visibly bold; never output bold=false.\n"
    "Do not interpret, classify, summarize, translate, normalize, or invent missing text.\n"
    "Use metadata only for non-secret OCR diagnostics, and omit metadata when empty.\n"
    "{source_filename_sentence}"
)


def responses_content_parts(assets: list[dict[str, str]], *, source_path: str | Path | None) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt_text(len(assets), source_path=source_path)}]
    for asset in assets:
        content.append({"type": "input_image", "image_url": asset["data_url"], "detail": "high"})
    return content


def chat_content_parts(assets: list[dict[str, str]], *, source_path: str | Path | None) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text(len(assets), source_path=source_path)}]
    for asset in assets:
        content.append({"type": "image_url", "image_url": {"url": asset["data_url"], "detail": "high"}})
    return content


def prompt_text(page_count: int, *, source_path: str | Path | None) -> str:
    source_name = Path(source_path).name if source_path else ""
    source_sentence = f"Source filename: {source_name}." if source_name else ""
    template = prompt_template()
    return (
        template.replace("{page_count}", str(page_count))
        .replace("{source_filename}", source_name)
        .replace("{source_filename_sentence}", source_sentence)
        .strip()
    )


def prompt_template() -> str:
    for candidate in prompt_template_candidates():
        if not candidate:
            continue
        try:
            text = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return text
    return DEFAULT_OCR_PROMPT_TEMPLATE


def prompt_template_candidates() -> list[Path]:
    candidates: list[Path] = []
    explicit = str(os.environ.get("OPTIMIZER_OCR_PROMPT_PATH") or "").strip()
    if explicit:
        candidates.append(Path(explicit))
    app_home = str(os.environ.get("OPTIMIZER_HOME") or "").strip()
    if app_home:
        candidates.append(Path(app_home) / "config" / PROMPT_FILE_NAME)
    candidates.append(Path(__file__).resolve().parents[1] / "config" / PROMPT_FILE_NAME)
    return candidates
