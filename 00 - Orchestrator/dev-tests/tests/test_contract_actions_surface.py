from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from orchestrator.orchestrator_contract.types import SUPPORTED_ACTIONS
from orchestrator.workspace_domain.policy import path_hash
from .contract_test_support import _run_contract, contract_module

def test_contract_reset_returns_summary(monkeypatch, tmp_path: Path) -> None:
    closed: list[bool] = []

    class FakeEngine:
        def reset_run_history(self, _ui_state):
            return type("ResetSummary", (), {"cleared_records": 5, "restored_sources": 4, "renamed_conflicts": 1, "removed_targets": 7})()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(tmp_path, {"action": "reset", "ui_state": {"input_folder": "in"}})

    assert payload == {"status": "ok", "cleared_records": 5, "restored_sources": 4, "renamed_conflicts": 1, "removed_targets": 7}
    assert closed == [True]

def test_contract_reset_pipeline_logs_returns_summary(monkeypatch, tmp_path: Path) -> None:
    closed: list[bool] = []

    class FakeEngine:
        def __init__(self) -> None:
            self._root = tmp_path
            self._project_state_dir = tmp_path / "state"

        def reset_pipeline_logs(self, _ui_state):
            return type("PipelineLogResetSummary", (), {"cleared_records": 3, "removed_pipeline_targets": ("state/pipeline",), "removed_log_targets": ()})()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)
    monkeypatch.setattr(contract_module, "_reset_logging_files", lambda _state_root: (tmp_path / "state" / "orchestrator.log",))

    payload = _run_contract(tmp_path, {"action": "reset_pipeline_logs", "ui_state": {}})

    assert payload == {"status": "ok", "cleared_records": 3, "removed_pipeline_targets": ["state/pipeline"], "removed_log_targets": ["state/orchestrator.log"]}
    assert closed == [True]

def test_contract_healthcheck_returns_ok(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(contract_module, "ensure_startup_prerequisites", lambda: {})

    payload = _run_contract(tmp_path, {"action": "healthcheck"})

    assert payload == {"status": "ok", "healthy": True, "message": "", "dependencies": []}

def test_contract_embeddings_returns_ok(monkeypatch, tmp_path: Path) -> None:
    closed: list[bool] = []

    class FakeEngine:
        def run_embeddings(self, _ui_state):
            return type("EmbeddingResult", (), {"status": "completed", "count": 7, "reason": "7 embeddings generated."})()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(tmp_path, {"action": "embeddings", "ui_state": {"input_folder": "in"}})

    assert payload == {"status": "completed", "count": 7, "reason": "7 embeddings generated."}
    assert closed == [True]

def test_contract_embeddings_adapter_call_returns_owner_result(monkeypatch, tmp_path: Path) -> None:
    closed: list[bool] = []
    corpus_db = tmp_path / "Corpus" / "rebuilt.db"

    class FakeEngine:
        def run_embeddings(self, _ui_state):
            return type("EmbeddingResult", (), {"status": "completed", "count": 7, "reason": "7 embeddings generated."})()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(
        tmp_path,
        {
            "schema_version": "adapter.call_request.v1",
            "request_payload": {
                "action": "embeddings",
                "ui_state": {"selected_corpus_db_path": str(corpus_db)},
            },
        },
    )

    assert payload["status"] == "ok"
    assert payload["output_refs"]["embedding_result"] == "completed"
    assert payload["output_refs"]["embedding_count"] == 7
    assert payload["target_identity_proof"]["database_path_hash"] == path_hash(corpus_db)
    assert closed == [True]

def test_contract_activate_corpus_context_persists_owner_ui_state(monkeypatch, tmp_path: Path) -> None:
    corpus_root = tmp_path / "Corpus"
    corpus_root.mkdir()
    corpus_db = corpus_root / "corpus.db"
    conn = sqlite3.connect(corpus_db)
    conn.close()
    monkeypatch.setattr(contract_module, "ORCHESTRATOR_ROOT", tmp_path)

    payload = _run_contract(
        tmp_path,
        {
            "action": "activate_corpus_context",
            "corpus_db_path": str(corpus_db),
            "corpus_output_folder": str(corpus_root),
        },
    )

    assert payload["status"] == "ok"
    assert payload["corpus_db_path"] == str(corpus_db.resolve())
    state = json.loads((tmp_path / "state" / "ui_state.json").read_text(encoding="utf-8"))
    assert state["selected_corpus_db_path"] == str(corpus_db.resolve())
    assert state["corpus_output_folder"] == str(corpus_root.resolve())
    assert state["semantic_release_mode"] == "database_default"
    assert state["semantic_release_path"] == ""

def test_contract_activate_corpus_context_can_switch_artifact_root(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifacts"
    input_root = artifact_root / "Input"
    input_root.mkdir(parents=True)
    corpus_root = artifact_root / "Corpus"
    corpus_root.mkdir(parents=True)
    corpus_db = corpus_root / "corpus.db"
    conn = sqlite3.connect(corpus_db)
    conn.close()
    monkeypatch.setattr(contract_module, "ORCHESTRATOR_ROOT", tmp_path)

    payload = _run_contract(
        tmp_path,
        {
            "action": "activate_corpus_context",
            "artifact_folder": str(artifact_root),
            "input_folder": str(input_root),
            "corpus_db_path": str(corpus_db),
            "corpus_output_folder": str(corpus_root),
        },
    )

    assert payload["status"] == "ok"
    assert payload["artifact_folder"] == str(artifact_root.resolve())
    assert payload["input_folder"] == str(input_root.resolve())
    state = json.loads((tmp_path / "state" / "ui_state.json").read_text(encoding="utf-8"))
    assert state["input_folder"] == str(input_root.resolve())
    assert state["artifact_folder"] == str(artifact_root.resolve())
    assert state["corpus_output_folder"] == str(corpus_root.resolve())
    assert state["selected_corpus_db_path"] == str(corpus_db.resolve())

def test_manifest_actions_match_supported_contract_actions() -> None:
    manifest_path = Path(__file__).resolve().parents[2] / "module-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["actions"] == list(SUPPORTED_ACTIONS)

def test_contract_unknown_action_returns_error(tmp_path: Path) -> None:
    payload = _run_contract(tmp_path, {"action": "unknown"})

    assert payload["status"] == "error"
    assert payload["reason"] == "Unknown action: unknown"
