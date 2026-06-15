from __future__ import annotations

from pathlib import Path

from corpus_builder.loader import load_from_file as _load_from_file


def _report_path(json_path: Path) -> Path:
    for suffix in (".vision_validation_report.json", ".validation_report.json"):
        candidate = json_path.with_name(json_path.name.replace(".structured.json", suffix))
        if candidate.exists():
            return candidate
    return json_path.with_name(json_path.name.replace(".structured.json", ".vision_validation_report.json"))


def load_from_file(db, json_path: Path):
    normalized_path = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
    return _load_from_file(
        db,
        normalized_path,
        _report_path(json_path),
        structured_path=json_path,
    )
