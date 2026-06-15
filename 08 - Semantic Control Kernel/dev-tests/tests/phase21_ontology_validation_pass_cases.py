from __future__ import annotations

import sqlite3
from pathlib import Path

from phase21_ontology_validation_schema import create_minimal_ontology_schema, insert_consistent_ontology_rows
from semantic_control_kernel.validation.ontology_validation import ontology_patch_validation


def test_ontology_patch_validation_passes_for_consistent_minimal_db(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        insert_consistent_ontology_rows(conn)
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path, ontology_id="lens_primary")

    assert report["status"] == "pass"
    assert not report["errors"]


def test_ontology_patch_validation_passes_base_graph_without_lenses(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    conn = sqlite3.connect(db_path)
    try:
        create_minimal_ontology_schema(conn)
        conn.executescript(
            """
            INSERT INTO documents (id, source_document_id, page_index) VALUES ('doc_1', 'source_1', 0);
            INSERT INTO relations (id) VALUES (1);
            INSERT INTO source_documents (source_document_id, metadata_json) VALUES ('source_1', '{}');
            INSERT INTO source_document_pages (source_document_id, document_id, page_index, evidence_json) VALUES ('source_1', 'doc_1', 0, '{}');
            INSERT INTO source_document_classifications (source_document_id, classification_scope, ontology_id, status, basis_json) VALUES ('source_1', 'base', NULL, 'materialized', '{}');
            INSERT INTO source_document_classifications (source_document_id, classification_scope, ontology_id, status, basis_json) VALUES ('source_1', 'semantic_release', NULL, 'materialized', '{}');
            INSERT INTO structural_units (unit_id, source_document_id, unit_type, parent_unit_id, document_id, page_index, metadata_json) VALUES ('su_source_1', 'source_1', 'base_unit', NULL, NULL, NULL, '{}');
            INSERT INTO structural_units (unit_id, source_document_id, unit_type, parent_unit_id, document_id, page_index, metadata_json) VALUES ('su_doc_1', 'source_1', 'page_unit', 'su_source_1', 'doc_1', 0, '{}');
            INSERT INTO structural_unit_relations (relation_id, source_document_id, source_unit_id, target_unit_id, relation_type, evidence_json) VALUES ('sur_1', 'source_1', 'su_source_1', 'su_doc_1', 'contains', '{}');
            """
        )
        conn.commit()
    finally:
        conn.close()

    report = ontology_patch_validation(db_path)

    assert report["status"] == "pass"
    assert not report["warnings"]
    assert not report["errors"]
