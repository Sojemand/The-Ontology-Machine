"""Named CLI command types shared across the Normalizer CLI stages."""
from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


@dataclass(frozen=True)
class CheckConfigCommand:
    config_path: str | None = None

    @classmethod
    def from_namespace(cls, args: Namespace) -> "CheckConfigCommand":
        return cls(_optional_string(getattr(args, "config", None)))


@dataclass(frozen=True)
class AnalyzeTaxonomyCommand:
    @classmethod
    def from_namespace(cls, _args: Namespace) -> "AnalyzeTaxonomyCommand":
        return cls()
