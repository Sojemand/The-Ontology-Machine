from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from corpus_builder.orchestrator_contract import main as contract_main, types, workflow

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_main_load_document_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    payload = {
        "action": "load_document",
        "normalized_path": str(tmp_path / "doc.structured.normalized.json"),
        "structured_path": str(tmp_path / "doc.structured.json"),
        "validation_path": str(tmp_path / "doc.validation_report.json"),
        "corpus_db_path": str(tmp_path / "corpus.db"),
    }
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_load_document(command, *, context) -> dict:
        captured["command"] = command
        captured["context"] = context
        return {"status": "loaded", "reason": ""}

    monkeypatch.setattr(workflow, "load_document", fake_load_document)

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    data = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert data == {"status": "loaded", "reason": ""}
    assert captured["command"] == types.LoadDocumentCommand(
        corpus_db_path=str(tmp_path / "corpus.db"),
        normalized_path=str(tmp_path / "doc.structured.normalized.json"),
        structured_path=str(tmp_path / "doc.structured.json"),
        validation_path=str(tmp_path / "doc.validation_report.json"),
    )


def test_main_healthcheck_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps(
            {
                "action": "healthcheck",
                "scope": "pipeline_run",
                "runtime_settings": {"model": "text-embedding-3-small"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        workflow,
        "healthcheck",
        lambda command, *, context: {
            "status": "ok",
            "healthy": True,
            "message": "",
            "dependencies": [],
            "scope": command.scope,
            "model": command.runtime_settings.model,
        },
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    data = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert data["status"] == "ok"
    assert data["healthy"] is True
    assert data["scope"] == "pipeline_run"
    assert data["model"] == "text-embedding-3-small"


def test_main_read_active_semantic_release_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(
        json.dumps({"action": "read_active_semantic_release", "corpus_db_path": str(tmp_path / "corpus.db")}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        workflow,
        "handle_read_active_semantic_release",
        lambda command, *, context: {
            "status": "ok",
            "headline": "Active semantic release loaded",
            "summary_lines": [],
            "artifacts": [],
            "detail": {
                "release_id": "semantic_release.default",
                "release_version": "1",
                "fingerprint": "sha256:test",
                "release_path": str(tmp_path / "state" / "semantic_release.active.json"),
                "status": {},
                "release": {"release_id": "semantic_release.default"},
            },
        },
    )

    exit_code = contract_main(["--request", str(request_path), "--response", str(response_path)])
    data = json.loads(response_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert data["status"] == "ok"
    assert data["detail"]["release_id"] == "semantic_release.default"


def test_main_unknown_action_returns_error(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "unknown"}), encoding="utf-8")

    contract_main(["--request", str(request_path), "--response", str(response_path)])
    data = json.loads(response_path.read_text(encoding="utf-8"))

    assert data["status"] == "error"
    assert data["reason"] == "Unbekannte Aktion: unknown"


def test_python_m_module_path_stays_startable(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps({"action": "unknown"}), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "corpus_builder.orchestrator_contract", "--request", str(request_path), "--response", str(response_path)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(response_path.read_text(encoding="utf-8"))

    assert completed.returncode == 0
    assert data["status"] == "error"
    assert data["reason"] == "Unbekannte Aktion: unknown"


def test_manifest_actions_match_contract_surface() -> None:
    manifest_path = PROJECT_ROOT / "module-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["launcher_module"] == "corpus_builder"
    assert manifest["contract_module"] == "corpus_builder.orchestrator_contract"
    assert manifest["actions"] == list(types.ACTION_NAMES)
    assert manifest["debug_surface"] == {
        "supports_scan": True,
        "supports_single": True,
        "supports_batch": True,
        "input_source": "module_selected_input",
        "output_source": "orchestrator_assigned_output",
        "controls": ["mode", "persist_page_images"],
        "artifacts": ["corpus_db", "preview_report", "load_report"],
    }
