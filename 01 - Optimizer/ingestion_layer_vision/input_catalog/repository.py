"""Persistence for processed-hash state files and import/export payloads."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from ..models import atomic_json_write
from .validation import parse_hash_payload

logger = logging.getLogger(__name__)

_PROCESSED_HASHES_FILE = "processed_hashes.json"


def processed_hashes_path(state_dir: Path | None) -> Path | None:
    if not state_dir:
        return None
    return Path(state_dir) / _PROCESSED_HASHES_FILE


def read_hashes_from_file(path: Path) -> set[str]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"ungueltige Hash-Datei: {exc}") from exc
    return parse_hash_payload(payload, Path(path).name, logger=logger)


def read_hashes_from_state(state_dir: Path | None) -> set[str]:
    hashes, _recovered = read_hashes_from_state_with_status(state_dir)
    return hashes


def read_hashes_from_state_with_status(state_dir: Path | None) -> tuple[set[str], bool]:
    state_path = processed_hashes_path(state_dir)
    if not state_path or not state_path.exists():
        return set(), False
    try:
        return read_hashes_from_file(state_path), False
    except (OSError, ValueError) as exc:
        logger.warning("processed_hashes.json konnte nicht geladen werden: %s", exc)
        return set(), True


def serialize_hashes(hashes: set[str]) -> dict[str, object]:
    return {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "hashes": sorted(hashes),
    }


def save_processed_hashes(state_dir: Path | None, hashes: set[str]) -> None:
    state_path = processed_hashes_path(state_dir)
    if not state_path:
        return
    try:
        atomic_json_write(state_path, serialize_hashes(hashes))
    except OSError as exc:
        logger.warning("processed_hashes.json konnte nicht geschrieben werden: %s", exc)


def export_hashes(target_path: Path, hashes: set[str]) -> None:
    atomic_json_write(Path(target_path), serialize_hashes(hashes))
