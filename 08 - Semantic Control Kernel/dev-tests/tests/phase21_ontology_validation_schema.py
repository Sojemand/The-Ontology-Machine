from __future__ import annotations

import sqlite3


def create_minimal_ontology_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE documents (id TEXT PRIMARY KEY, source_document_id TEXT, page_index INTEGER);
        CREATE TABLE relations (id INTEGER PRIMARY KEY);
        CREATE TABLE source_documents (source_document_id TEXT PRIMARY KEY, metadata_json TEXT);
        CREATE TABLE source_document_pages (source_document_id TEXT, document_id TEXT, page_index INTEGER, evidence_json TEXT);
        CREATE TABLE source_document_classifications (source_document_id TEXT, classification_scope TEXT, ontology_id TEXT, status TEXT, basis_json TEXT);
        CREATE TABLE structural_units (unit_id TEXT PRIMARY KEY, source_document_id TEXT, unit_type TEXT, parent_unit_id TEXT, document_id TEXT, page_index INTEGER, metadata_json TEXT);
        CREATE TABLE structural_unit_relations (relation_id TEXT PRIMARY KEY, source_document_id TEXT, source_unit_id TEXT, target_unit_id TEXT, relation_type TEXT, evidence_json TEXT);
        CREATE TABLE ontology_lenses (ontology_id TEXT PRIMARY KEY, status TEXT, intent_json TEXT, policy_json TEXT);
        CREATE TABLE ontology_runs (run_id TEXT PRIMARY KEY, ontology_id TEXT, checkpoint_json TEXT, stats_json TEXT);
        CREATE TABLE ontology_terms (term_id TEXT PRIMARY KEY, ontology_id TEXT, aliases_json TEXT);
        CREATE TABLE ontology_nodes (node_id TEXT PRIMARY KEY, ontology_id TEXT, source_ref_type TEXT, source_ref_id TEXT, status TEXT, attributes_json TEXT);
        CREATE TABLE ontology_edges (edge_id TEXT PRIMARY KEY, ontology_id TEXT, source_node_id TEXT, target_node_id TEXT, status TEXT, attributes_json TEXT);
        CREATE TABLE ontology_assertions (assertion_id TEXT PRIMARY KEY, ontology_id TEXT, subject_ref_type TEXT, subject_ref_id TEXT, predicate TEXT, object_ref_type TEXT, object_ref_id TEXT, status TEXT);
        CREATE TABLE ontology_evidence_links (evidence_link_id TEXT PRIMARY KEY, ontology_id TEXT, target_type TEXT, target_id TEXT, evidence_ref_type TEXT, evidence_ref_id TEXT);
        CREATE TABLE ontology_activation (ontology_id TEXT, is_active INTEGER, is_primary INTEGER);
        CREATE TABLE ontology_embedding_chunks (chunk_id TEXT PRIMARY KEY, ontology_id TEXT, object_type TEXT, object_id TEXT, source_refs_json TEXT);
        CREATE TABLE ontology_edit_log (edit_id TEXT PRIMARY KEY, ontology_id TEXT, affected_tables_json TEXT, affected_rows_json TEXT, before_rows_json TEXT, after_rows_json TEXT);
        CREATE TABLE evidence_atoms (atom_id INTEGER PRIMARY KEY);
        CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY);
        CREATE TABLE extracted_fields (id INTEGER PRIMARY KEY);
        CREATE TABLE extracted_rows (id INTEGER PRIMARY KEY);
        """
    )


def insert_consistent_ontology_rows(conn: sqlite3.Connection) -> None:
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
        INSERT INTO ontology_lenses (ontology_id, status, intent_json, policy_json) VALUES ('lens_primary', 'ready', '{}', '{}');
        INSERT INTO ontology_activation (ontology_id, is_active, is_primary) VALUES ('lens_primary', 1, 1);
        INSERT INTO ontology_runs (run_id, ontology_id, checkpoint_json, stats_json) VALUES ('run_1', 'lens_primary', '{}', '{}');
        INSERT INTO ontology_terms (term_id, ontology_id, aliases_json) VALUES ('term_1', 'lens_primary', '[]');
        INSERT INTO ontology_nodes (node_id, ontology_id, source_ref_type, source_ref_id, status, attributes_json) VALUES ('node_a', 'lens_primary', 'document', 'doc_1', 'verified', '{}');
        INSERT INTO ontology_nodes (node_id, ontology_id, source_ref_type, source_ref_id, status, attributes_json) VALUES ('node_b', 'lens_primary', 'term', 'term_1', 'draft', '{}');
        INSERT INTO ontology_edges (edge_id, ontology_id, source_node_id, target_node_id, status, attributes_json) VALUES ('edge_1', 'lens_primary', 'node_a', 'node_b', 'draft', '{}');
        INSERT INTO ontology_assertions (assertion_id, ontology_id, subject_ref_type, subject_ref_id, predicate, object_ref_type, object_ref_id, status) VALUES ('assertion_1', 'lens_primary', 'node', 'node_a', 'classified_as', 'term', 'term_1', 'verified');
        INSERT INTO evidence_atoms (atom_id) VALUES (1);
        INSERT INTO document_promotions (promotion_id) VALUES (1);
        INSERT INTO extracted_fields (id) VALUES (1);
        INSERT INTO extracted_rows (id) VALUES (1);
        INSERT INTO ontology_evidence_links (evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id) VALUES ('ev_1', 'lens_primary', 'node', 'node_a', 'document', 'doc_1');
        INSERT INTO ontology_evidence_links (evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id) VALUES ('ev_2', 'lens_primary', 'assertion', 'assertion_1', 'document', 'doc_1');
        INSERT INTO ontology_embedding_chunks (chunk_id, ontology_id, object_type, object_id, source_refs_json) VALUES ('chunk_1', 'lens_primary', 'node', 'node_a', '[]');
        INSERT INTO ontology_edit_log (edit_id, ontology_id, affected_tables_json, affected_rows_json, before_rows_json, after_rows_json) VALUES ('edit_1', 'lens_primary', '[]', '{}', '{}', '{}');
        """
    )
