"""Policy stage for standalone artifact-sidecar selection."""

from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_VALIDATION_SUFFIXES = (
    ".vision_validation_report.json",
    ".files_validation_report.json",
    ".validation_report.json",
)
_PROFILE_VALIDATION_SUFFIXES = {
    "vision": (".vision_validation_report.json", ".validation_report.json", ".files_validation_report.json"),
    "file": (".files_validation_report.json", ".validation_report.json", ".vision_validation_report.json"),
}


def _structured_interpreter_profile(structured_path: Path | None) -> str | None:
    if structured_path is None or not structured_path.exists() or not structured_path.is_file():
        return None
    try:
        payload = json.loads(structured_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    processing = payload.get("processing") if isinstance(payload, dict) else None
    profile = str(processing.get("interpreter_profile") or "").strip().lower() if isinstance(processing, dict) else ""
    return profile or None


def validation_suffixes_for_structured(structured_path: Path | None) -> tuple[str, ...]:
    profile = _structured_interpreter_profile(structured_path)
    return _PROFILE_VALIDATION_SUFFIXES.get(profile, _DEFAULT_VALIDATION_SUFFIXES)
