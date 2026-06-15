"""Named CLI command types shared across Validator Vision main stages."""
from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


@dataclass(frozen=True)
class ValidateCommand:
    structured_path: Path
    report_path: Path
    config_path: str | None = None
    raw_path: Path | None = None
    raw_root: Path | None = None

    @classmethod
    def from_namespace(cls, args: Namespace) -> "ValidateCommand":
        raw_path = _optional_string(getattr(args, "raw", None))
        raw_root = _optional_string(getattr(args, "raw_root", None))
        return cls(
            Path(args.structured),
            Path(args.report),
            _optional_string(getattr(args, "config", None)),
            Path(raw_path) if raw_path is not None else None,
            Path(raw_root) if raw_root is not None else None,
        )


@dataclass(frozen=True)
class ValidateBatchCommand:
    structured_dir: Path
    report_root: Path
    config_path: str | None = None
    raw_root: Path | None = None

    @classmethod
    def from_namespace(cls, args: Namespace) -> "ValidateBatchCommand":
        raw_root = _optional_string(getattr(args, "raw_root", None))
        return cls(
            Path(args.structured),
            Path(args.report_root),
            _optional_string(getattr(args, "config", None)),
            Path(raw_root) if raw_root is not None else None,
        )
