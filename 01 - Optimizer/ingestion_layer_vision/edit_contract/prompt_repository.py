"""Prompt surface helpers for the Optimizer edit contract."""
from __future__ import annotations

from typing import Any

from optimizer_ocr.workflow import DEFAULT_OCR_PROMPT_TEMPLATE, PROMPT_FILE_NAME
from ..models.repository import atomic_text_write

PROMPT_FIELD = "ocr_prompt_md"


def read_ocr_prompt(layout) -> dict[str, str]:
    path = layout.config_dir / PROMPT_FILE_NAME
    if path.exists():
        return {PROMPT_FIELD: path.read_text(encoding="utf-8")}
    source = layout.bundled_config_dir / PROMPT_FILE_NAME
    if source.exists():
        return {PROMPT_FIELD: source.read_text(encoding="utf-8")}
    return {PROMPT_FIELD: DEFAULT_OCR_PROMPT_TEMPLATE}


def validate_ocr_prompt(payload: dict[str, Any]) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("optimizer.ocr_prompt muss ein JSON-Objekt sein.")
    missing = [PROMPT_FIELD] if PROMPT_FIELD not in payload else []
    extras = [field for field in payload if field != PROMPT_FIELD]
    if missing or extras:
        details = []
        if missing:
            details.append(f"fehlend: {', '.join(missing)}")
        if extras:
            details.append(f"unerlaubt: {', '.join(extras)}")
        raise ValueError(f"optimizer.ocr_prompt hat ungueltige Felder ({'; '.join(details)}).")
    text = str(payload.get(PROMPT_FIELD) or "").strip()
    if not text:
        raise ValueError("optimizer.ocr_prompt darf nicht leer sein.")
    if "{page_count}" not in text:
        raise ValueError("optimizer.ocr_prompt muss den Platzhalter {page_count} enthalten.")
    return {PROMPT_FIELD: text}


def write_ocr_prompt(layout, payload: dict[str, Any]) -> dict[str, str]:
    normalized = validate_ocr_prompt(payload)
    path = layout.config_dir / PROMPT_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_text_write(path, normalized[PROMPT_FIELD] + "\n")
    return read_ocr_prompt(layout)
