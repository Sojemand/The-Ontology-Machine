from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_path_text(path: str | os.PathLike[str]) -> str:
    resolved = Path(path).resolve(strict=False)
    text = str(resolved).replace("\\", "/")
    anchor = resolved.anchor.replace("\\", "/").rstrip("/")
    if anchor and text.rstrip("/") != anchor:
        text = text.rstrip("/")
    if os.name == "nt" or resolved.drive:
        text = text.casefold()
    return text


def path_hash(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(canonical_path_text(path).encode("utf-8")).hexdigest()[:24]


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
