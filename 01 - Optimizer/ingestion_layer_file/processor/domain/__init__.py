"""Stable processor-domain surface with an explicit build contract."""
from __future__ import annotations

from .block_domain import parse_blocks
from .extract_domain import build_extract
from .types import BuildExtractRequest

__all__ = ["BuildExtractRequest", "build_extract", "parse_blocks"]
