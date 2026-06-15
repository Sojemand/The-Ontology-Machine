"""Named boundary types for structured input documents."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StructuredDocument:
    path: Path
    payload: dict[str, Any]

