from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from mcp_server import support_monitor

def _artifact_args(paths: dict[str, str], *, include_corpus_db: bool = True) -> dict[str, str]:
    args = {
        "pipeline_root": paths["pipeline_root"],
        "normalized_dir": paths["normalized_dir"],
        "structured_dir": paths["structured_dir"],
        "validation_dir": paths["validation_dir"],
        "raw_dir": paths["raw_dir"],
    }
    if include_corpus_db:
        args["corpus_db_path"] = paths["active_db"]
    return args


def _workspace_paths(paths: dict[str, str]) -> dict[str, str]:
    artifact = Path(paths["workspace_artifact_root"]).resolve()
    return {
        "artifact": str(artifact),
        "input": str(artifact / "Input"),
        "corpus": str(artifact / "Corpus"),
        "db": str(artifact / "Corpus" / "Fantasy_Story.db"),
    }


def _working_workspace_paths(paths: dict[str, str]) -> dict[str, str]:
    artifact = Path(paths["working_workspace_artifact_root"]).resolve()
    return {
        "artifact": str(artifact),
        "input": str(artifact / "Input"),
        "corpus": str(artifact / "Corpus"),
        "db": str(artifact / "Corpus" / "Fantasy_Story.db"),
        "release": str(artifact / "Corpus" / "Fantasy_Story.semantic_release.json"),
    }


def _reset_workspace_paths(paths: dict[str, str]) -> dict[str, str]:
    artifact = Path(paths["reset_workspace_artifact_root"]).resolve()
    return {
        "artifact": str(artifact),
        "input": str(artifact / "Input"),
        "corpus": str(artifact / "Corpus"),
        "db": str(artifact / "Corpus" / "Fantasy_Story.db"),
        "release": str(artifact / "Corpus" / "Fantasy_Story.semantic_release.json"),
        "confirmation": str(artifact / "Corpus" / "Fantasy_Story.reset.confirmation.json"),
    }


def _support_incident(paths: dict[str, str]) -> str:
    result = support_monitor.record_event(
        {
            "module_key": "corpus_builder",
            "action": "activation_preflight",
            "severity": "error",
            "status": "exception",
            "message": f"Release validation failed in {paths['pipeline_root']}",
            "exception_type": "RuntimeError",
            "stacktrace": "Traceback...\nRuntimeError: validation failed",
        }
    )
    return str(result["incident"]["incident_id"])


def _support_assessment(paths: dict[str, str]) -> str:
    result = support_monitor.assess_incident(
        {
            "classification": "unexpected_exception",
            "confidence": "high",
            "module_key": "corpus_builder",
            "tool_action": "activation_preflight",
            "severity": "error",
            "status": "exception",
            "message": f"Release validation failed in {paths['pipeline_root']}",
            "exception_type": "RuntimeError",
            "stacktrace": "Traceback...\nRuntimeError: validation failed",
        }
    )
    return str(result["assessment"]["assessment_id"])


def _support_queue_args(paths: dict[str, str]) -> dict[str, str | bool]:
    assessment_id = _support_assessment(paths)
    assessment = support_monitor.require_assessment(assessment_id)
    built = support_monitor.build_bug_report(
        incident_id=str(assessment["incident_id"]),
        output_path=paths["bug_report_path"],
    )
    return {"assessment_id": assessment_id, "report_path": str(built["report_path"]), "user_confirmed": True}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_empty_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.close()
