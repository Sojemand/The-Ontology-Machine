"""Boundary I/O for local prompt override bundles."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .contract import default_prompt_bundle_payload
from .types import PROMPT_FIELDS, PromptBundle

logger = logging.getLogger(__name__)


def load_prompt_bundle(bundle_path: Path, overrides_path: Path | None = None) -> PromptBundle:
    merged = default_prompt_bundle_payload()
    base_payload = _read_prompt_mapping(bundle_path, label="Prompt-Bundle")
    if base_payload is not None:
        try:
            merged = _normalize_prompt_payload(base_payload, allow_partial=False)
        except ValueError as exc:
            logger.warning("Prompt-Bundle konnte nicht geladen werden: %s", exc)
    override_payload = _read_prompt_mapping(overrides_path, label="Prompt-Overrides")
    if override_payload is not None:
        try:
            overrides = _normalize_prompt_payload(override_payload, allow_partial=True)
        except ValueError as exc:
            logger.warning("Prompt-Overrides konnten nicht geladen werden: %s", exc)
        else:
            for key, value in overrides.items():
                if value.strip():
                    merged[key] = value
    return PromptBundle(prompts=merged)


def _read_prompt_mapping(path: Path | None, *, label: str) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("%s konnten nicht geladen werden: %s", label, exc)
        return None
    if not isinstance(data, dict):
        logger.warning("%s muss ein JSON-Objekt sein.", label)
        return None
    return data


def _normalize_prompt_payload(payload: dict[str, object], *, allow_partial: bool) -> dict[str, str]:
    unknown = sorted(set(payload) - set(PROMPT_FIELDS))
    if unknown:
        raise ValueError(f"Prompt-Payload enthaelt unbekannte Felder: {', '.join(unknown)}")
    if not allow_partial:
        missing = [field_name for field_name in PROMPT_FIELDS if field_name not in payload]
        if missing:
            raise ValueError(f"Prompt-Payload enthaelt fehlende Felder: {', '.join(missing)}")
    normalized: dict[str, str] = {}
    for field_name in PROMPT_FIELDS:
        if field_name not in payload:
            continue
        value = payload[field_name]
        if not isinstance(value, str):
            raise ValueError(f"{field_name} muss ein String sein.")
        normalized[field_name] = value
    return normalized


__all__ = ["load_prompt_bundle"]
