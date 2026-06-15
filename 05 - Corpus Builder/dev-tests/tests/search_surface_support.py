from __future__ import annotations

from pathlib import Path

from corpus_builder.loader import load_from_file as _load_from_file
from corpus_builder.models import EmbeddingRuntimeSettings

RUNTIME_SETTINGS = EmbeddingRuntimeSettings(model="test-model")


def report_path_for(json_path: Path) -> Path:
    for suffix in (".vision_validation_report.json", ".validation_report.json"):
        candidate = json_path.with_name(json_path.name.replace(".structured.json", suffix))
        if candidate.exists():
            return candidate
    return json_path.with_name(json_path.name.replace(".structured.json", ".vision_validation_report.json"))


def load_from_file(db, json_path: Path, *, semantic_release=None):
    normalized_path = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
    return _load_from_file(
        db,
        normalized_path,
        report_path_for(json_path),
        structured_path=json_path,
        semantic_release=semantic_release,
    )
