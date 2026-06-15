from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.database import connect, connect_readonly
from corpus_builder.semantic_release.multi_source_merge_preflight import multi_source_merge_preflight
from corpus_builder.semantic_release.multi_source_merge_workflow import multi_source_merge_databases

from .multi_source_merge_support import selection, source_database


def test_filled_merge_preserves_base_graph_and_ontology_lenses(tmp_path: Path) -> None:
    artifact_root = tmp_path / "Merge Root"
    (artifact_root / "Corpus").mkdir(parents=True, exist_ok=True)
    merge_selection = selection(artifact_root, "filled")
    source_database(artifact_root, "db_a", "source_doc_a", "sha256:content_a")
    source_database(artifact_root, "db_b", "source_doc_b", "sha256:content_b")
    _attach_base_graph_and_lens(artifact_root / "source_a.db", "source_doc_a", "A")
    _attach_base_graph_and_lens(artifact_root / "source_b.db", "source_doc_b", "B")

    multi_source_merge_preflight({"selection": merge_selection})
    merged = multi_source_merge_databases({"selection": merge_selection, "mode": "additive"})

    assert merged["status"] == "ok"
    conn = connect_readonly(str(artifact_root / "Corpus" / "merged.db"))
    try:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM source_document_pages").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM structural_units").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM structural_unit_relations").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ontology_lenses").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ontology_nodes").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM ontology_edges").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ontology_assertions").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ontology_evidence_links").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ontology_embedding_chunks").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM source_document_classifications WHERE classification_scope = 'ontology'").fetchone()[0] == 2

        source_ids = [row[0] for row in conn.execute("SELECT source_document_id FROM source_documents ORDER BY source_document_id")]
        assert len(set(source_ids)) == 2
        assert "source_doc_shared" not in source_ids
        document_source_ids = [row[0] for row in conn.execute("SELECT source_document_id FROM documents ORDER BY id")]
        assert set(document_source_ids) == set(source_ids)

        lens_ids = [row[0] for row in conn.execute("SELECT ontology_id FROM ontology_lenses ORDER BY ontology_id")]
        assert len(set(lens_ids)) == 2
        assert "lens_shared" not in lens_ids
        assert conn.execute("SELECT COUNT(*) FROM ontology_lenses WHERE parent_ontology_id = ontology_id").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM ontology_activation WHERE is_active = 1").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ontology_activation WHERE is_active = 1 AND is_primary = 1").fetchone()[0] == 1

        stale_refs = conn.execute(
            "SELECT COUNT(*) FROM ontology_nodes WHERE source_ref_id IN ('source_doc_shared', 'source_doc_a', 'source_doc_b')"
        ).fetchone()[0]
        assert stale_refs == 0
        relation_hints = [row[0] for row in conn.execute("SELECT target_hint FROM relations WHERE relation_origin = 'base_graph'")]
        assert relation_hints and "source_doc_shared" not in relation_hints
        source_refs_json = conn.execute("SELECT source_refs_json FROM ontology_embedding_chunks LIMIT 1").fetchone()[0]
        assert "source_doc_shared" not in source_refs_json
    finally:
        conn.close()


def _attach_base_graph_and_lens(db_path: Path, document_id: str, label: str) -> None:
    conn = connect(str(db_path))
    try:
        atom_id = _insert_evidence_atom(conn, document_id, label)
        conn.execute(
            "UPDATE documents SET source_document_id = ?, source_uri = ?, source_artifact_id = ?, ingest_run_id = ?, "
            "page_index = 0, page_label = ?, source_content_hash = ? WHERE id = ?",
            ("source_doc_shared", f"file://{label}", f"artifact_{label}", f"ingest_{label}", "1", f"source_hash_{label}", document_id),
        )
        conn.execute(
            "INSERT INTO source_documents (source_document_id, source_uri, source_artifact_id, ingest_run_id, source_title, "
            "source_kind, page_count, first_document_id, last_document_id, source_content_hash, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "source_doc_shared",
                f"file://{label}",
                f"artifact_{label}",
                f"ingest_{label}",
                f"Source {label}",
                "document",
                1,
                document_id,
                document_id,
                f"source_hash_{label}",
                json.dumps({"document_id": document_id, "source_document_id": "source_doc_shared"}),
            ),
        )
        conn.execute(
            "INSERT INTO source_document_pages (source_document_id, document_id, page_index, page_label, evidence_json) VALUES (?, ?, ?, ?, ?)",
            ("source_doc_shared", document_id, 0, "1", json.dumps({"document_id": document_id})),
        )
        conn.execute(
            "INSERT INTO source_document_classifications (source_document_id, classification_scope, document_type, category, confidence, status, basis_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("source_doc_shared", "base", "invoice", "finance", 1.0, "materialized", "{}"),
        )
        conn.execute(
            "INSERT INTO structural_units (unit_id, source_document_id, unit_type, ordinal, label, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
            ("unit_base", "source_doc_shared", "base_unit", 0, f"Base {label}", "{}"),
        )
        conn.execute(
            "INSERT INTO structural_units (unit_id, source_document_id, unit_type, parent_unit_id, document_id, page_index, ordinal, label, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("unit_page", "source_doc_shared", "page_unit", "unit_base", document_id, 0, 0, f"Page {label}", "{}"),
        )
        conn.execute(
            "INSERT INTO structural_unit_relations (relation_id, source_document_id, source_unit_id, target_unit_id, relation_type, evidence_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("unit_rel", "source_doc_shared", "unit_base", "unit_page", "contains", "{}"),
        )
        conn.execute(
            "INSERT INTO relations (document_id, relation_type, target_hint, relation_origin, status, evidence_refs) VALUES (?, ?, ?, ?, ?, ?)",
            (
                document_id,
                "page_of_source_document",
                "source_doc_shared",
                "base_graph",
                "materialized",
                json.dumps({"source_document_id": "source_doc_shared", "document_id": document_id}),
            ),
        )
        _insert_lens(conn, document_id, label, atom_id)
        conn.commit()
    finally:
        conn.close()


def _insert_evidence_atom(conn, document_id: str, label: str) -> int:
    cursor = conn.execute(
        "INSERT INTO evidence_atoms (document_id, atom_type, json_path, text_value, normalized_text, compact_text) VALUES (?, ?, ?, ?, ?, ?)",
        (document_id, "field", "$.title", f"Evidence {label}", f"evidence {label.lower()}", f"evidence{label.lower()}"),
    )
    return int(cursor.lastrowid)


def _insert_lens(conn, document_id: str, label: str, atom_id: int) -> None:
    conn.execute(
        "INSERT INTO ontology_lenses (ontology_id, name, description, status, parent_ontology_id, intent_json, policy_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("lens_shared", f"Lens {label}", "Preservation test lens", "ready", "lens_shared", "{}", "{}"),
    )
    conn.execute(
        "INSERT INTO ontology_activation (ontology_id, is_active, is_primary) VALUES (?, ?, ?)",
        ("lens_shared", 1, 1),
    )
    conn.execute(
        "INSERT INTO ontology_runs (run_id, ontology_id, run_kind, goal, status, checkpoint_json, stats_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("run_shared", "lens_shared", "extend", "preserve", "complete", "{}", "{}"),
    )
    conn.execute(
        "INSERT INTO source_document_classifications (source_document_id, classification_scope, ontology_id, document_type, category, confidence, status, basis_json, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("source_doc_shared", "ontology", "lens_shared", "lens_type", f"category_{label}", 0.9, "materialized", "{}", "ontology_agent"),
    )
    conn.execute(
        "INSERT INTO ontology_terms (term_id, ontology_id, label, normalized_label, term_kind, aliases_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("term_shared", "lens_shared", f"Theme {label}", f"theme {label.lower()}", "theme", "[]", "verified"),
    )
    conn.execute(
        "INSERT INTO ontology_nodes (node_id, ontology_id, node_type, canonical_label, source_ref_type, source_ref_id, attributes_json, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("node_source", "lens_shared", "source_document", f"Source node {label}", "source_document", "source_doc_shared", "{}", "verified"),
    )
    conn.execute(
        "INSERT INTO ontology_nodes (node_id, ontology_id, node_type, canonical_label, source_ref_type, source_ref_id, attributes_json, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("node_document", "lens_shared", "document", f"Document node {label}", "document", document_id, "{}", "verified"),
    )
    conn.execute(
        "INSERT INTO ontology_edges (edge_id, ontology_id, source_node_id, target_node_id, relation_type, attributes_json, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("edge_shared", "lens_shared", "node_source", "node_document", "contains", "{}", "verified"),
    )
    conn.execute(
        "INSERT INTO ontology_assertions (assertion_id, ontology_id, subject_ref_type, subject_ref_id, predicate, object_ref_type, object_ref_id, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("assertion_shared", "lens_shared", "source_document", "source_doc_shared", "has_node", "node", "node_document", "verified"),
    )
    conn.execute(
        "INSERT INTO ontology_evidence_links (evidence_link_id, ontology_id, run_id, target_type, target_id, evidence_ref_type, evidence_ref_id, quote, rationale) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("evidence_shared", "lens_shared", "run_shared", "node", "node_source", "evidence_atom", str(atom_id), "quote", "rationale"),
    )
    conn.execute(
        "INSERT INTO ontology_embedding_chunks (chunk_id, ontology_id, run_id, object_type, object_id, chunk_index, chunk_type, source_kind, source_refs_json, chunk_text, vector, model, dimensions) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "chunk_shared",
            "lens_shared",
            "run_shared",
            "node",
            "node_source",
            0,
            "summary",
            "ontology",
            json.dumps({"source_document_id": "source_doc_shared", "document_id": document_id}),
            "Source node text",
            b"1234",
            "test-embedding",
            4,
        ),
    )
