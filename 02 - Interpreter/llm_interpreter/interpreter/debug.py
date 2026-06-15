"""Debug bundle helpers for staged interpreter runs."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models import InterpreterConfig, atomic_json_write
from .adapter import safe_generated_file_name
from .types import DebugBundleState

logger = logging.getLogger(__name__)


def write_debug_bundle(
    config: InterpreterConfig,
    state: DebugBundleState,
    *,
    failed_stage: str | None,
    error: Exception | None,
) -> Path | None:
    target_dir = config.debug_bundle_dir
    if target_dir is None:
        return None
    target_dir = Path(target_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / _bundle_name(state.label)
    payload = {
        "label": state.label,
        "request_path": state.request_path,
        "failed_stage": failed_stage,
        "error": None if error is None else str(error),
        "message_snapshot": state.message_snapshot,
        "raw_provider_text": state.raw_provider_text,
        "parsed_payload": state.parsed_payload,
        "persisted_payload": state.persisted_payload,
    }
    try:
        atomic_json_write(target_path, _prune_none(payload))
        return target_path
    except Exception:
        logger.exception("Debug bundle konnte nicht geschrieben werden")
        return None


def _bundle_name(label: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return safe_generated_file_name(label, f".{stamp}.debug.json", fallback_stem="request")


def _prune_none(value):
    if isinstance(value, dict):
        return {key: _prune_none(child) for key, child in value.items() if child not in (None, "", [], {})}
    if isinstance(value, list):
        return [_prune_none(item) for item in value if item not in (None, "", [], {})]
    return value


__all__ = ["write_debug_bundle"]
