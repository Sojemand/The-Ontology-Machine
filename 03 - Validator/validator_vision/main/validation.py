"""CLI validation stage for hard boundary checks."""
from __future__ import annotations

from pathlib import Path


class CliUsageError(ValueError):
    """Raised when CLI arguments reference unusable paths."""


def require_structured_file(path: Path) -> Path:
    if not path.exists():
        raise CliUsageError(f"Structured JSON nicht gefunden: {path}")
    if not path.is_file():
        raise CliUsageError(f"Structured JSON muss eine Datei sein: {path}")
    return path


def require_structured_dir(path: Path) -> Path:
    if not path.is_dir():
        raise CliUsageError(f"Verzeichnis nicht gefunden: {path}")
    return path


def require_report_path(path: Path) -> Path:
    if path.exists() and not path.is_file():
        raise CliUsageError(f"Report-Ziel muss eine Datei sein: {path}")
    return path


def require_report_root(path: Path) -> Path:
    if path.exists() and not path.is_dir():
        raise CliUsageError(f"Report-Root muss ein Verzeichnis sein: {path}")
    return path


def require_optional_file(path: Path | None, *, label: str) -> Path | None:
    if path is None:
        return None
    if not path.exists():
        raise CliUsageError(f"{label} nicht gefunden: {path}")
    if not path.is_file():
        raise CliUsageError(f"{label} muss eine Datei sein: {path}")
    return path


def require_optional_dir(path: Path | None, *, label: str) -> Path | None:
    if path is None:
        return None
    if not path.exists():
        raise CliUsageError(f"{label} nicht gefunden: {path}")
    if not path.is_dir():
        raise CliUsageError(f"{label} muss ein Verzeichnis sein: {path}")
    return path


def require_report_file(path: Path) -> Path:
    if not path.exists():
        raise CliUsageError(f"Report nicht gefunden: {path}")
    if not path.is_file():
        raise CliUsageError(f"Report muss eine Datei sein: {path}")
    return path
