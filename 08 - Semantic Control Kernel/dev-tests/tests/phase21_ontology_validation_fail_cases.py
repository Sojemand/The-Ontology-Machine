from __future__ import annotations

import sqlite3
from pathlib import Path

from phase21_ontology_validation_schema import create_minimal_ontology_schema, insert_consistent_ontology_rows
from semantic_control_kernel.validation.ontology_validation import ontology_patch_validation


def test_ontology_patch_validation_fails_edge_lens_mismatch(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        insert_consistent_ontology_rows(conn)
        conn.execute("INSERT INTO ontology_lenses (ontology_id, status, intent_json, policy_json) VALUES ('other', 'draft', '{}', '{}')")
        conn.execute("INSERT INTO ontology_nodes (node_id, ontology_id, attributes_json) VALUES ('foreign_node', 'other', '{}')")
        conn.execute(
            "INSERT INTO ontology_edges (edge_id, ontology_id, source_node_id, target_node_id, attributes_json) "
            "VALUES ('bad_edge', 'lens_primary', 'node_a', 'foreign_node', '{}')"
        )
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path, ontology_id="lens_primary")

    assert report["status"] == "fail"
    assert any(error["code"] == "edge_lens_mismatch" for error in report["errors"])


def test_ontology_patch_validation_fails_missing_object_identifiers(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        insert_consistent_ontology_rows(conn)
        conn.execute("INSERT INTO ontology_nodes (node_id, ontology_id, attributes_json) VALUES (NULL, 'lens_primary', '{}')")
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path, ontology_id="lens_primary")

    assert report["status"] == "fail"
    assert any(error["code"] == "missing_required_object_identifiers" for error in report["errors"])


def test_ontology_patch_validation_fails_active_primary_draft_lens(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        insert_consistent_ontology_rows(conn)
        conn.execute("UPDATE ontology_lenses SET status = 'draft' WHERE ontology_id = 'lens_primary'")
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path, ontology_id="lens_primary")

    assert report["status"] == "fail"
    assert any(error["code"] == "primary_lens_not_ready" for error in report["errors"])


def test_ontology_patch_validation_fails_dangling_semantic_refs(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        insert_consistent_ontology_rows(conn)
        conn.execute("UPDATE ontology_nodes SET source_ref_type = 'term', source_ref_id = 'missing_term' WHERE node_id = 'node_b'")
        conn.execute(
            "UPDATE ontology_assertions SET subject_ref_id = 'Missing Node Label', object_ref_id = 'missing_term' "
            "WHERE assertion_id = 'assertion_1'"
        )
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path, ontology_id="lens_primary")

    assert report["status"] == "fail"
    assert any(error["code"] == "missing_node_source_refs" for error in report["errors"])
    assert any(error["code"] == "missing_assertion_subject_refs" for error in report["errors"])
    assert any(error["code"] == "missing_assertion_object_refs" for error in report["errors"])


def test_ontology_patch_validation_fails_verified_objects_without_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        insert_consistent_ontology_rows(conn)
        conn.execute("UPDATE ontology_nodes SET status = 'verified' WHERE node_id = 'node_b'")
        conn.execute("INSERT INTO ontology_assertions (assertion_id, ontology_id, subject_ref_type, subject_ref_id, predicate, status) VALUES ('assertion_without_evidence', 'lens_primary', 'node', 'node_a', 'notes', 'verified')")
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path, ontology_id="lens_primary")

    assert report["status"] == "fail"
    assert any(error["code"] == "verified_objects_without_evidence" for error in report["errors"])
