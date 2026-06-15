from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.tool_contract_matrix_helpers import _write_empty_sqlite, _write_json

@pytest.fixture()
def mcp_files(tmp_path: Path) -> dict[str, str]:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    artifact_root = tmp_path / "artifacts"
    normalized_dir = artifact_root / "normalized"
    structured_dir = artifact_root / "structured"
    validation_dir = artifact_root / "validation"
    raw_dir = artifact_root / "raw"
    for folder in (normalized_dir, structured_dir, validation_dir, raw_dir):
        folder.mkdir(parents=True)
    normalized_artifact = normalized_dir / "invoice.structured.normalized.json"
    structured_artifact = structured_dir / "invoice.structured.json"
    validation_artifact = validation_dir / "invoice.validation_report.json"
    raw_artifact = raw_dir / "invoice.raw.json"
    page_images_dir = artifact_root / "page_images" / "invoice"
    page_images_dir.mkdir(parents=True)
    _write_json(normalized_artifact, {"projection": {"projection_id": "finance.default.v1"}, "content": {"fields": {}}})
    _write_json(structured_artifact, {"processing": {"interpreter_profile": "vision"}, "content": {"fields": {}}})
    _write_json(validation_artifact, {"status": "passed", "issues": []})
    _write_json(raw_artifact, {"raw": True})

    active_db = corpus_root / "active.db"
    active_db.write_bytes(b"SQLite format 3\x00")
    source_db = corpus_root / "source.db"
    source_db.write_bytes(b"SQLite format 3\x00")
    target_db = corpus_root / "target.db"
    target_db.write_bytes(b"SQLite format 3\x00")

    release_path = tmp_path / "releases" / "release.semantic_release.json"
    _write_json(release_path, {"release_id": "fixture", "version": "1.0.0"})
    exported_release = tmp_path / "releases" / "exported.semantic_release.json"
    sample_document = tmp_path / "samples" / "Fantasy Story.txt"
    sample_document.parent.mkdir()
    sample_document.write_text("The moonlit tower watched the vanished prince.", encoding="utf-8")
    interpreter_request = tmp_path / "samples" / "interpreter.request.json"
    structured_sample = tmp_path / "samples" / "structured.sample.json"
    normalizer_structured = tmp_path / "samples" / "story.structured.json"
    expected_normalized = tmp_path / "samples" / "expected.normalized.json"
    _write_json(interpreter_request, {"source": {"file_name": "Fantasy Story.txt"}, "page_assets": [{"path": str(sample_document)}]})
    _write_json(structured_sample, {"classification": {"document_type": "story"}, "content": {"fields": {"character": "prince"}}})
    _write_json(normalizer_structured, {"classification": {"document_type": "story"}, "content": {"fields": {"character": "prince"}}})
    _write_json(expected_normalized, {"classification": {"document_type": "story"}, "content": {"fields": {"character": "prince"}}})
    run_artifact_root = tmp_path / "run-workspace"
    run_input = run_artifact_root / "Input"
    run_corpus = run_artifact_root / "Corpus"
    debug_root = run_artifact_root / "Debug"
    run_input.mkdir(parents=True)
    run_corpus.mkdir(parents=True)
    debug_root.mkdir(parents=True)
    run_db = run_corpus / "active-run.db"
    _write_empty_sqlite(run_db)
    (run_input / "story.txt").write_text("The moonlit tower watched the vanished prince.", encoding="utf-8")
    reset_workspace_artifact_root = tmp_path / "reset-workspace-artifacts"
    reset_workspace_corpus = reset_workspace_artifact_root / "Corpus"
    reset_workspace_corpus.mkdir(parents=True)
    reset_workspace_db = reset_workspace_corpus / "Fantasy_Story.db"
    _write_empty_sqlite(reset_workspace_db)
    orchestrator_ui_state_path = tmp_path / "orchestrator-state" / "ui_state.json"
    _write_json(
        orchestrator_ui_state_path,
        {
            "input_folder": str(run_input),
            "artifact_folder": str(run_artifact_root),
            "corpus_output_folder": str(run_corpus),
            "selected_corpus_db_path": str(run_db),
            "semantic_release_mode": "database_default",
            "semantic_release_path": "",
            "mode": "single",
        },
    )

    confirmation = tmp_path / "confirmations" / "reset-active-corpus.json"
    _write_json(
        confirmation,
        {
            "artifact_version": "reset_active_corpus_db_confirmation_v1",
            "requested_action": "reset_active_corpus_db",
            "confirmed": True,
            "corpus_db_path": str(active_db),
        },
    )
    activation_confirmation = tmp_path / "confirmations" / "activate-release.json"
    _write_json(activation_confirmation, {"confirmed": True, "purpose": "activate release in MCP test"})
    snapshot_confirmation = tmp_path / "confirmations" / "snapshot-risk.json"
    _write_json(snapshot_confirmation, {"confirmed": True, "purpose": "merge snapshot risk in MCP test"})
    collision_resolution = tmp_path / "confirmations" / "collision-resolution.json"
    _write_json(collision_resolution, {"strategy": "prefer_target"})

    return {
        "corpus_root": str(corpus_root),
        "active_db": str(active_db),
        "fresh_db": str(corpus_root / "fresh.db"),
        "blueprint_db": str(corpus_root / "blueprint.db"),
        "source_db": str(source_db),
        "target_db": str(target_db),
        "release_path": str(release_path),
        "exported_release": str(exported_release),
        "sample_document": str(sample_document),
        "interpreter_request": str(interpreter_request),
        "structured_sample": str(structured_sample),
        "normalizer_structured": str(normalizer_structured),
        "expected_normalized": str(expected_normalized),
        "run_artifact_root": str(run_artifact_root),
        "run_input": str(run_input),
        "run_corpus": str(run_corpus),
        "debug_root": str(debug_root),
        "run_db": str(run_db),
        "orchestrator_ui_state_path": str(orchestrator_ui_state_path),
        "confirmation": str(confirmation),
        "activation_confirmation": str(activation_confirmation),
        "snapshot_confirmation": str(snapshot_confirmation),
        "collision_resolution": str(collision_resolution),
        "pipeline_root": str(tmp_path),
        "artifact_root": str(artifact_root),
        "normalized_dir": str(normalized_dir),
        "structured_dir": str(structured_dir),
        "validation_dir": str(validation_dir),
        "raw_dir": str(raw_dir),
        "normalized_artifact": str(normalized_artifact),
        "structured_artifact": str(structured_artifact),
        "validation_artifact": str(validation_artifact),
        "raw_artifact": str(raw_artifact),
        "page_images_dir": str(page_images_dir),
        "workspace_artifact_root": str(tmp_path / "workspace-artifacts"),
        "working_workspace_artifact_root": str(tmp_path / "working-workspace-artifacts"),
        "reset_workspace_artifact_root": str(reset_workspace_artifact_root),
        "working_release_path": str(tmp_path / "working-workspace-artifacts" / "Corpus" / "Fantasy_Story.semantic_release.json"),
        "export_path": str(tmp_path / "exports" / "corpus.jsonl"),
        "support_root": str(tmp_path / "support"),
        "pipeline_runs_dir": str(tmp_path / "mcp-runs"),
        "bug_report_path": str(tmp_path / "reports" / "support-report.json"),
    }
