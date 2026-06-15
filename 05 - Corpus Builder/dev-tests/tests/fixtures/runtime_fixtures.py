"""Runtime and file-writing fixtures for Corpus Builder tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from corpus_builder.database import ensure_schema
from corpus_builder.models import CorpusConfig


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _default_normalized_payload(structured: dict) -> dict:
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


@pytest.fixture()
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


@pytest.fixture()
def default_config() -> CorpusConfig:
    return CorpusConfig()


@pytest.fixture()
def make_input_pair(tmp_path: Path):
    def _make(
        base_name: str,
        structured: dict,
        *,
        vision_report: dict | None = None,
        files_report: dict | None = None,
        legacy_report: dict | None = None,
        normalized: dict | None = None,
        raw: dict | None = None,
    ) -> Path:
        json_path = tmp_path / f"{base_name}.structured.json"
        _write_json(json_path, structured)
        if vision_report is not None:
            _write_json(tmp_path / f"{base_name}.vision_validation_report.json", vision_report)
        if files_report is not None:
            _write_json(tmp_path / f"{base_name}.files_validation_report.json", files_report)
        if legacy_report is not None:
            _write_json(tmp_path / f"{base_name}.validation_report.json", legacy_report)
        _write_json(
            tmp_path / f"{base_name}.structured.normalized.json",
            normalized if normalized is not None else _default_normalized_payload(structured),
        )
        if raw is not None:
            _write_json(tmp_path / f"{base_name}.raw.json", raw)
        return json_path

    return _make
