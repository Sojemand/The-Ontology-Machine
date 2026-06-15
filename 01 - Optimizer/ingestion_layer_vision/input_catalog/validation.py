"""Hard invariants for hashes, UUIDs, path bounds and hash payload shape."""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_hash_value(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None

    digest = raw
    if raw.lower().startswith("sha256:"):
        digest = raw.split(":", 1)[1].strip()

    digest = digest.lower()
    if not _SHA256_RE.fullmatch(digest):
        return None
    return f"sha256:{digest}"


def is_valid_uuid_text(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return False
    try:
        uuid.UUID(raw)
    except ValueError:
        return False
    return True


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def parse_hash_payload(
    payload: object,
    source_name: str,
    *,
    logger: logging.Logger | None = None,
) -> set[str]:
    active_logger = logger or logging.getLogger(__name__)
    hashes: list[str] | None = None
    if isinstance(payload, dict):
        candidate = payload.get("hashes", [])
        if isinstance(candidate, list):
            hashes = candidate
    elif isinstance(payload, list):
        hashes = payload

    if hashes is None:
        raise ValueError("Hash-Datei enthaelt kein gueltiges 'hashes'-Array")

    normalized_hashes: set[str] = set()
    invalid_count = 0
    for value in hashes:
        if not isinstance(value, str) or not value.strip():
            continue
        normalized = normalize_hash_value(value)
        if normalized is None:
            invalid_count += 1
            continue
        normalized_hashes.add(normalized)

    if invalid_count:
        active_logger.warning(
            "%s enthaelt %d ungueltige Hash-Eintraege; sie werden ignoriert",
            source_name,
            invalid_count,
        )
    return normalized_hashes
