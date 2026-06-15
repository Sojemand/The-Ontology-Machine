"""Stable plugin manager surface for the Optimizer."""
from __future__ import annotations

import os
import subprocess as subprocess

_SUBPROCESS_ENV = {**os.environ, "PYTHONUTF8": "1"}

from .policy import _INLINE_EXTRACTORS
from .surface import ExtractorRegistry
from .types import _InlineRuntime

PluginManager = ExtractorRegistry

__all__ = [
    "ExtractorRegistry",
    "PluginManager",
    "_InlineRuntime",
    "_INLINE_EXTRACTORS",
    "_SUBPROCESS_ENV",
    "subprocess",
]

