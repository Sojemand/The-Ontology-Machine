"""Hashing helpers for processor repository state."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def compute_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                hasher.update(chunk)
    except OSError as exc:
        logger.warning("Hash-Berechnung fehlgeschlagen fuer %s: %s", file_path, exc)
        return ""
    return f"sha256:{hasher.hexdigest()}"
