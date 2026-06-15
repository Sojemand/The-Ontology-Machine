from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from .contract_test_support import _insert_document_rows, _run_contract, contract_module

def test_contract_run_owner_call_returns_pipeline_evidence(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    db_path = artifact_root / "Corpus" / "active.db"
    db_path.parent.mkdir(parents=True)
    captured_hashes: list[set[str]] = []

    class FakeEngine:
        def __init__(self, *, snapshot_callback=None) -> None:
            self._state = SimpleNamespace(documents={})

        def run(self, _ui_state, *, owner_input_hashes=None):
            captured_hashes.append(set(owner_input_hashes or ()))
            return SimpleNamespace(
                total=1,
                success=1,
                errors=0,
                needs_review=0,
                retries=0,
                run_id="orch_run",
                run_log_path=str(artifact_root / "Documents" / "logs" / "run.log"),
                tracked_hashes=(),
            )

        def close(self) -> None:
            pass

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(
        tmp_path,
        {
            "schema_version": "adapter.call_request.v1",
            "request_payload": {
                "action": "run",
                "ui_state": {
                    "artifact_folder": str(artifact_root),
                    "selected_corpus_db_path": str(db_path),
                },
                "pipeline_batch_id": "pbt_contract",
                "target_identity": {
                    "database_path_hash": "dbhash",
                    "artifact_root_path_hash": "roothash",
                },
                "input_files": [{"content_hash": "sha256:allowed"}],
            },
        },
    )

    assert payload["status"] == "ok"
    assert payload["output_refs"]["pipeline_batch_id"] == "pbt_contract"
    assert payload["output_refs"]["owner_run_refs"]["orchestrator_run_id"] == "orch_run"
    assert payload["target_identity_proof"]["database_path_hash"] == "dbhash"
    assert captured_hashes == [{"sha256:allowed"}]

def test_contract_run_owner_evidence_correlates_materialized_rows_by_source_name(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    db_path = artifact_root / "Corpus" / "active.db"
    _insert_document_rows(
        db_path,
        [
            {
                "id": "doc.pdf",
                "file_name": "doc.pdf",
                "source_file_path": "../source/doc.pdf",
                "source_page": 1,
                "content_hash": "sha256:materialized_content",
            }
        ],
    )

    class FakeEngine:
        def __init__(self, *, snapshot_callback=None) -> None:
            self._state = SimpleNamespace(
                documents={
                    "sha256:original_file": SimpleNamespace(
                        content_hash="sha256:original_file",
                        file_name="doc.pdf",
                        relative_path="doc.pdf",
                        original_source_path=str(artifact_root / "Input" / "doc.pdf"),
                        source_path=str(artifact_root / "Documents" / "originals" / "doc.pdf"),
                        final_disposition="needs_review",
                        status="success",
                        artifacts=None,
                    )
                }
            )

        def run(self, _ui_state, *, owner_input_hashes=None):
            return SimpleNamespace(total=1, success=1, errors=0, needs_review=1, retries=0, run_id="orch_run", run_log_path=str(artifact_root / "Documents" / "logs" / "run.log"), tracked_hashes=())

        def close(self) -> None:
            pass

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(
        tmp_path,
        {
            "schema_version": "adapter.call_request.v1",
            "request_payload": {
                "action": "run",
                "ui_state": {"artifact_folder": str(artifact_root), "selected_corpus_db_path": str(db_path)},
                "pipeline_batch_id": "pbt_contract",
                "input_files": [{"input_file_id": "inp_1", "content_hash": "sha256:original_file", "input_relative_path": "Input/doc.pdf"}],
            },
        },
    )

    output = payload["output_refs"]
    assert output["input_file_dispositions"] == [{"input_file_id": "inp_1", "pipeline_batch_id": "pbt_contract", "disposition": "materialized"}]
    assert [record["document_id"] for record in output["materialized_records"]] == ["doc.pdf"]
    assert "content_hash" not in output["materialized_records"][0]

def test_contract_run_owner_evidence_keeps_pagewise_materialization_records(monkeypatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "Artifact Tree"
    db_path = artifact_root / "Corpus" / "active.db"
    _insert_document_rows(
        db_path,
        [
            {"id": "doc.p002", "file_name": "doc.pdf", "source_file_path": "../source/doc.pdf", "source_page": 2, "content_hash": "sha256:p2"},
            {"id": "doc.p001", "file_name": "doc.pdf", "source_file_path": "../source/doc.pdf", "source_page": 1, "content_hash": "sha256:p1"},
        ],
    )

    class FakeEngine:
        def __init__(self, *, snapshot_callback=None) -> None:
            self._state = SimpleNamespace(
                documents={
                    "sha256:original_file": SimpleNamespace(
                        content_hash="sha256:original_file",
                        file_name="doc.pdf",
                        relative_path="doc.pdf",
                        original_source_path=str(artifact_root / "Input" / "doc.pdf"),
                        source_path=str(artifact_root / "Documents" / "originals" / "doc.pdf"),
                        final_disposition="success",
                        status="success",
                        artifacts=None,
                    )
                }
            )

        def run(self, _ui_state, *, owner_input_hashes=None):
            return SimpleNamespace(total=1, success=1, errors=0, needs_review=0, retries=0, run_id="orch_run", run_log_path=str(artifact_root / "Documents" / "logs" / "run.log"), tracked_hashes=())

        def close(self) -> None:
            pass

    monkeypatch.setattr(contract_module, "OrchestratorEngine", FakeEngine)

    payload = _run_contract(
        tmp_path,
        {
            "schema_version": "adapter.call_request.v1",
            "request_payload": {
                "action": "run",
                "ui_state": {"artifact_folder": str(artifact_root), "selected_corpus_db_path": str(db_path)},
                "pipeline_batch_id": "pbt_contract",
                "input_files": [{"input_file_id": "inp_1", "content_hash": "sha256:original_file", "input_relative_path": "Input/doc.pdf"}],
            },
        },
    )

    records = payload["output_refs"]["materialized_records"]
    assert [record["document_id"] for record in records] == ["doc.p001", "doc.p002"]
    assert payload["output_refs"]["record_counts"]["documents"] == 2
