from __future__ import annotations

import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from mcp_server.tools import call_tool
from tests.tool_subprocess_seed import _seed_document

def _export_default_release(output_path: str) -> str:
    result = call_tool(
        "export_default_blueprint_release",
        {"blueprint_ref": "default", "target_locale": "en", "output_path": output_path},
    )
    assert result["status"] == "OK"
    return str(result["output_path"])


def _write_reset_confirmation(paths: dict[str, str], db_path: str) -> Path:
    path = Path(paths["confirmation_dir"]) / "reset-active-corpus.json"
    _write_json(
        path,
        {
            "artifact_version": "reset_active_corpus_db_confirmation_v1",
            "requested_action": "reset_active_corpus_db",
            "confirmed": True,
            "corpus_db_path": db_path,
            "reason": "l2 integration test",
        },
    )
    return path


def _write_new_corpus_confirmation(
    paths: dict[str, str],
    *,
    label: str = "l2_new_corpus",
    action: str,
) -> Path:
    path = Path(paths["confirmation_dir"]) / f"{label}.json"
    _write_json(
        path,
        {
            "artifact_version": "new_corpus_db_confirmation_v1",
            "requested_action": action,
            "confirmed": True,
            "database_label": label,
            "taxonomy_locale": "en",
        },
    )
    return path


def _write_empty_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.close()


def _copy_regression_artifacts(target_root: Path) -> None:
    source_root = (
        Path(__file__).resolve().parents[3]
        / "05 - Corpus Builder"
        / "dev-tests"
        / "tests"
        / "fixtures"
        / "regression"
        / "vision_invoice"
    )
    normalized = target_root / "normalized"
    structured = target_root / "structured"
    validation = target_root / "validation"
    for folder in (normalized, structured, validation):
        folder.mkdir(parents=True)
    normalized_path = normalized / "invoice.structured.normalized.json"
    shutil.copy2(source_root / "invoice.structured.normalized.json", normalized_path)
    shutil.copy2(source_root / "invoice.structured.json", structured / "invoice.structured.json")
    shutil.copy2(source_root / "invoice.vision_validation_report.json", validation / "invoice.vision_validation_report.json")
    normalized_payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    normalized_payload.setdefault("projection", {})["projection_id"] = "finance.default.v1"
    normalized_payload["projection"]["projection_version"] = "v1"
    _write_json(normalized_path, normalized_payload)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
