"""Interpreter-profile constants and report suffix policy."""
from __future__ import annotations

VISION_PROFILE = "vision"
FILE_PROFILE = "file"
TABLE_PROFILE = "table"
SUPPORTED_PROFILES = {VISION_PROFILE, FILE_PROFILE, TABLE_PROFILE}


def require_supported_profile(profile: str) -> str:
    normalized = str(profile or "").strip().lower()
    if normalized not in SUPPORTED_PROFILES:
        raise ValueError(f"Unbekanntes processing.interpreter_profile: {profile!r}")
    return normalized


def report_suffix(profile: str) -> str:
    normalized = require_supported_profile(profile)
    if normalized == FILE_PROFILE:
        return ".files_validation_report.json"
    return ".vision_validation_report.json"


__all__ = [
    "FILE_PROFILE",
    "SUPPORTED_PROFILES",
    "TABLE_PROFILE",
    "VISION_PROFILE",
    "report_suffix",
    "require_supported_profile",
]
