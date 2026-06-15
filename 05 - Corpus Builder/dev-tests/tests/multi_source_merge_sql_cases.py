from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from corpus_builder.database import connect, connect_readonly, ensure_schema
from corpus_builder.orchestrator_contract.validation_suite import (
    parse_multi_source_merge_preflight_command,
    parse_write_merge_reconciliation_manifest_command,
)
from corpus_builder.semantic_release import multi_source_merge_sql_copy, multi_source_merge_sql_entities
from corpus_builder.semantic_release.multi_source_merge_preflight import multi_source_merge_preflight
from corpus_builder.semantic_release.multi_source_merge_sql_copy import merge_sql_databases
from corpus_builder.semantic_release.multi_source_merge_workflow import multi_source_merge_databases
from corpus_builder.semantic_release.sql_parameter_batches import iter_parameter_batches

from .multi_source_merge_support import load_artifact_json, request_fingerprint, selection, source_database


def test_multi_source_merge_preflight_treats_mixed_sources_as_filled_additive(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    merge_selection = selection(artifact_root, "filled")
    merge_selection["source_databases"][1]["source_state"] = "empty"
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")

    preflight = multi_source_merge_preflight({"selection": merge_selection})

    assert preflight["status"] == "ok"
    assert preflight["output_refs"]["source_class"] == "filled"
    assert preflight["output_refs"]["is_mixed_source_class"] is True


def test_multi_source_merge_databases_skips_empty_sources_in_filled_additive_mode(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    merge_selection["source_databases"][1]["source_state"] = "empty"
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")

    multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "additive"})

    assert merged["status"] == "ok"
    assert merged["output_refs"]["record_counts"]["documents"] == 1
    assert merged["output_refs"]["artifact_copy_report"]["copied_artifact_count"] == 1


def test_merge_sql_rejects_missing_source_database_without_creating_file(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    missing_source = Path(merge_selection["source_databases"][0]["source_database_path"])

    with pytest.raises(ValueError, match="source_database_missing"):
        merge_sql_databases(
            merge_selection,
            [
                {
                    "source_database_id": "db_a",
                    "source_document_id": "source_doc_a",
                    "target_document_id": "target_doc_a",
                    "target_artifact_path": "Documents/originals/source_doc_a.pdf",
                }
            ],
        )

    assert not missing_source.exists()


def test_multi_source_merge_cleans_staged_artifacts_when_sql_rejects_target(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")
    merge_selection["source_databases"][1]["source_state"] = "empty"
    _write_existing_target_document(Path(merge_selection["target_database_path"]))

    multi_source_merge_preflight({"selection": merge_selection})

    with pytest.raises(ValueError, match="target_database_not_empty"):
        multi_source_merge_databases({"selection": merge_selection, "mode": "additive"})

    target_artifact = artifact_root / "Documents" / "originals" / "source_doc_a.pdf"
    staging_root = artifact_root / "Documents" / "logs" / "merge_runs" / "merge_phase19" / "artifact_staging"
    stage_manifest_path = artifact_root / "Documents" / "logs" / "merge_runs" / "merge_phase19" / "artifact_stage_manifest.json"
    stage_manifest = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
    assert not target_artifact.exists()
    assert not staging_root.exists()
    assert stage_manifest["status"] == "sql_failed_staging_cleanup"
    assert stage_manifest["cleanup_report"]["cleanup_status"] == "removed"


def test_multi_source_merge_chunks_semantic_evidence_subject_queries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    merge_selection["source_databases"][1]["source_state"] = "empty"
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")
    _add_semantic_evidence_rows(artifact_root / "source_a.db", "source_doc_a", row_count=60)

    def limited_connect_readonly(path: str) -> sqlite3.Connection:
        conn = connect_readonly(path)
        if not hasattr(conn, "setlimit"):
            pytest.skip("sqlite connection limits unavailable on this Python build")
        conn.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 50)
        return conn

    def small_parameter_batches(values, *, reserved_parameters: int = 0, batch_size: int = 40):
        return iter_parameter_batches(values, reserved_parameters=reserved_parameters, batch_size=batch_size)

    monkeypatch.setattr(multi_source_merge_sql_copy, "connect_readonly", limited_connect_readonly)
    monkeypatch.setattr(multi_source_merge_sql_entities, "iter_parameter_batches", small_parameter_batches)

    multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "additive"})

    assert merged["status"] == "ok"
    conn = connect(str(artifact_root / "Corpus" / "merged.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM document_entities").fetchone()[0] == 60
        assert conn.execute("SELECT COUNT(*) FROM entity_attributes").fetchone()[0] == 60
        assert conn.execute("SELECT COUNT(*) FROM semantic_evidence_links").fetchone()[0] == 120
    finally:
        conn.close()


def test_multi_source_merge_reuses_original_artifact_for_page_scoped_rows(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    merge_selection["source_databases"][1]["source_state"] = "empty"
    _source_database_with_page_scoped_rows(artifact_root)

    multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "additive"})

    assert merged["status"] == "ok"
    assert merged["output_refs"]["record_counts"]["documents"] == 2
    assert merged["output_refs"]["artifact_copy_report"]["copied_artifact_count"] == 1
    id_map = load_artifact_json(artifact_root, merged["output_refs"]["merge_id_map_ref"])["mappings"]
    assert {
        item["target_artifact_path"]
        for item in id_map
    } == {"Documents/originals/order_1.pdf"}

    target_originals = list((artifact_root / "Documents" / "originals").rglob("*.pdf"))
    assert [path.relative_to(artifact_root).as_posix() for path in target_originals] == [
        "Documents/originals/order_1.pdf"
    ]
    conn = connect(str(artifact_root / "Corpus" / "merged.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(DISTINCT file_path) FROM documents").fetchone()[0] == 1
    finally:
        conn.close()


def test_parse_multi_source_merge_preflight_requires_request_fingerprint(tmp_path: Path) -> None:
    merge_selection = selection(tmp_path / "Merge Root", "empty")
    payload = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "multi_source_merge_preflight",
        "workflow_run_id": "wr_merge",
        "adapter_call_id": "adc_merge",
        "requested_at": "2026-05-07T00:00:00Z",
        "selection": merge_selection,
        "target_identity": {"merge_run_id": merge_selection["merge_run_id"]},
    }
    payload["request_fingerprint"] = request_fingerprint(payload)
    payload.pop("request_fingerprint")

    with pytest.raises(ValueError, match="request_fingerprint"):
        parse_multi_source_merge_preflight_command(payload)


def test_parse_write_merge_reconciliation_manifest_keeps_receipt_envelope_closed(tmp_path: Path) -> None:
    merge_selection = selection(tmp_path / "Merge Root", "empty")
    payload = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": "write_merge_reconciliation_manifest",
        "workflow_run_id": "wr_merge",
        "adapter_call_id": "adc_merge",
        "requested_at": "2026-05-28T00:00:00Z",
        "merge_run_id": merge_selection["merge_run_id"],
        "target_artifact_root": merge_selection["target_artifact_root"],
        "target_database_path": merge_selection["target_database_path"],
        "collision_manifest": {
            "manifest_fingerprint": "sha256:manifest",
            "target_database_path": merge_selection["target_database_path"],
        },
        "selected_resolutions": [],
        "target_identity": {"merge_run_id": merge_selection["merge_run_id"]},
    }
    payload["request_fingerprint"] = request_fingerprint(payload)

    parsed = parse_write_merge_reconciliation_manifest_command(payload)

    assert parsed.payload["target_database_path"] == merge_selection["target_database_path"]

    invalid = dict(payload)
    invalid["reconciliation_receipt"] = {}
    with pytest.raises(ValueError, match="reconciliation_receipt"):
        parse_write_merge_reconciliation_manifest_command(invalid)


def _add_semantic_evidence_rows(db_path: Path, document_id: str, *, row_count: int) -> None:
    conn = connect(str(db_path))
    try:
        for index in range(row_count):
            atom_id = conn.execute(
                "INSERT INTO evidence_atoms (document_id, atom_type, json_path, text_value) VALUES (?, ?, ?, ?)",
                (document_id, "field", f"$.items[{index}].value", f"value {index}"),
            ).lastrowid
            entity_id = conn.execute(
                "INSERT INTO document_entities (document_id, entity_key, entity_type, display_value) VALUES (?, ?, ?, ?)",
                (document_id, f"entity_{index}", "line_item", f"Item {index}"),
            ).lastrowid
            attribute_id = conn.execute(
                "INSERT INTO entity_attributes (entity_id, attribute_code, display_value) VALUES (?, ?, ?)",
                (entity_id, "amount", str(index)),
            ).lastrowid
            conn.execute(
                "INSERT INTO semantic_evidence_links (subject_kind, subject_id, atom_id, evidence_role) VALUES (?, ?, ?, ?)",
                ("document_entity", entity_id, atom_id, "source"),
            )
            conn.execute(
                "INSERT INTO semantic_evidence_links (subject_kind, subject_id, atom_id, evidence_role) VALUES (?, ?, ?, ?)",
                ("entity_attribute", attribute_id, atom_id, "source"),
            )
        conn.commit()
    finally:
        conn.close()


def _write_existing_target_document(db_path: Path) -> None:
    conn = connect(str(db_path))
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO documents (id, file_name, file_path, source_file_path, content_hash, document_type, category, language, model, model_confidence, materialization_version, projection_id, projection_fingerprint, validator_status, loaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                "existing_doc",
                "existing.pdf",
                str(db_path.parent / "existing.pdf"),
                str(db_path.parent / "existing.pdf"),
                "sha256:existing",
                "invoice",
                "finance",
                "de",
                "test-model",
                0.9,
                "v1",
                "projection_existing",
                "sha256:projection_existing",
                "pass",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _source_database_with_page_scoped_rows(root: Path) -> None:
    source_root = root / "source_a"
    original = source_root / "Documents" / "originals" / "order_1.pdf"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(b"shared order pdf")
    conn = connect(str(root / "source_a.db"))
    try:
        ensure_schema(conn)
        for page in (1, 2):
            document_id = f"order_1.pdf.p{page:03d}.of002"
            conn.execute(
                "INSERT INTO documents (id, file_name, file_path, source_file_path, content_hash, document_type, category, language, model, model_confidence, materialization_version, projection_id, projection_fingerprint, validator_status, loaded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    document_id,
                    "order_1.pdf",
                    f"../../source/order_1.pdf::page={page:03d}-of-002",
                    "../../source/order_1.pdf",
                    f"sha256:page_{page}",
                    "invoice",
                    "finance",
                    "de",
                    "test-model",
                    0.9,
                    "v1",
                    "projection_db_a",
                    "sha256:projection_db_a",
                    "pass",
                ),
            )
            conn.execute(
                "INSERT INTO document_payloads (document_id, schema_version, structured_json, normalized_json, release_fingerprint, loaded_at) "
                "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (document_id, "test.v1", "{}", "{}", "fp_a"),
            )
            conn.execute(
                "INSERT INTO document_processing_state (document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id, projection_fingerprint, materialization_state, source_mode, last_materialized_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    document_id,
                    "state.v1",
                    "v1",
                    "fp_a",
                    "projection_db_a",
                    "sha256:projection_db_a",
                    "current",
                    "structured",
                ),
            )
        conn.commit()
    finally:
        conn.close()
