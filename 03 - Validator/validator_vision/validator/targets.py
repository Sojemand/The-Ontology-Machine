"""Named validation targets shared across validator stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.types import StructuredDocument


@dataclass(frozen=True)
class ValidationTarget:
    structured_path: Path
    report_path: Path
    raw_path: Path | None = None
    document: StructuredDocument | None = None


__all__ = ["ValidationTarget"]
