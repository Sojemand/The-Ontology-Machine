"""Loader test I/O helpers for sidecar-aware fixture files."""

from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.loader import load_from_file as _load_from_file


def _normalized_payload_from_structured(structured: dict) -> dict:
    classification = structured.get("classification") if isinstance(structured.get("classification"), dict) else {}
    context = structured.get("context") if isinstance(structured.get("context"), dict) else {}
    content = structured.get("content") if isinstance(structured.get("content"), dict) else {"fields": {}, "rows": []}
    payload = {
        "classification": classification,
        "context": context,
        "content": content,
    }
    if isinstance(structured.get("projection"), dict):
        payload["projection"] = structured["projection"]
    if isinstance(structured.get("processing"), dict):
        payload["processing"] = structured["processing"]
    if isinstance(structured.get("relations"), list):
        payload["relations"] = structured["relations"]
    return payload


def vision_report_path(json_path: Path) -> Path:
    return json_path.with_name(json_path.name.replace(".structured.json", ".vision_validation_report.json"))


def files_report_path(json_path: Path) -> Path:
    return json_path.with_name(json_path.name.replace(".structured.json", ".files_validation_report.json"))


def legacy_report_path(json_path: Path) -> Path:
    return json_path.with_name(json_path.name.replace(".structured.json", ".validation_report.json"))


def report_path(json_path: Path) -> Path:
    for candidate in (vision_report_path(json_path), files_report_path(json_path), legacy_report_path(json_path)):
        if candidate.exists():
            return candidate
    return vision_report_path(json_path)


def normalized_path(json_path: Path) -> Path | None:
    candidate = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
    return candidate if candidate.exists() else None


def raw_path(json_path: Path) -> Path | None:
    candidate = json_path.with_name(json_path.name.replace(".structured.json", ".raw.json"))
    return candidate if candidate.exists() else None


def load_input_file(db, json_path: Path, **kwargs):
    validation_path = kwargs.pop("validation_path", None) or report_path(json_path)
    normalized_file = kwargs.pop("normalized_path", None) or normalized_path(json_path)
    raw_file = kwargs.pop("raw_path", None) or raw_path(json_path)
    if normalized_file is None:
        normalized_file = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
        structured = json.loads(json_path.read_text(encoding="utf-8"))
        normalized_file.write_text(
            json.dumps(_normalized_payload_from_structured(structured), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return _load_from_file(
        db,
        normalized_file,
        validation_path,
        structured_path=kwargs.pop("structured_path", None) or json_path,
        raw_path=raw_file,
        **kwargs,
    )


def write_structured_pair(tmp_path: Path, base_name: str, structured: dict, report: dict) -> Path:
    json_path = tmp_path / f"{base_name}.structured.json"
    json_path.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding="utf-8")
    json_path.with_name(f"{base_name}.structured.normalized.json").write_text(
        json.dumps(_normalized_payload_from_structured(structured), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    vision_report_path(json_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return json_path
