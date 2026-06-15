"""Stable plugin manager surface for the Optimizer."""
from __future__ import annotations

from .policy import _INLINE_EXTRACTORS
from .surface import ExtractorRegistry
from .types import _InlineRuntime

PluginManager = ExtractorRegistry

__all__ = [
    "ExtractorRegistry",
    "PluginManager",
    "_InlineRuntime",
    "_INLINE_EXTRACTORS",
]
