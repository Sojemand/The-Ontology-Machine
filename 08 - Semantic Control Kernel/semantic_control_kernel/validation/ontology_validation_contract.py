from __future__ import annotations


REQUIRED_ONTOLOGY_TABLES: tuple[str, ...] = (
    "documents", "relations", "source_documents", "source_document_pages",
    "source_document_classifications", "structural_units", "structural_unit_relations",
    "ontology_lenses", "ontology_runs", "ontology_terms", "ontology_nodes",
    "ontology_edges", "ontology_assertions", "ontology_evidence_links",
    "ontology_activation", "ontology_embedding_chunks", "ontology_edit_log",
)

JSON_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("source_documents", "source_document_id", "metadata_json"),
    ("source_document_pages", "document_id", "evidence_json"),
    ("source_document_classifications", "source_document_id", "basis_json"),
    ("structural_units", "unit_id", "metadata_json"),
    ("structural_unit_relations", "relation_id", "evidence_json"),
    ("ontology_lenses", "ontology_id", "intent_json"),
    ("ontology_lenses", "ontology_id", "policy_json"),
    ("ontology_runs", "run_id", "checkpoint_json"),
    ("ontology_runs", "run_id", "stats_json"),
    ("ontology_terms", "term_id", "aliases_json"),
    ("ontology_nodes", "node_id", "attributes_json"),
    ("ontology_edges", "edge_id", "attributes_json"),
    ("ontology_embedding_chunks", "chunk_id", "source_refs_json"),
    ("ontology_edit_log", "edit_id", "affected_tables_json"),
    ("ontology_edit_log", "edit_id", "affected_rows_json"),
    ("ontology_edit_log", "edit_id", "before_rows_json"),
    ("ontology_edit_log", "edit_id", "after_rows_json"),
)

SEMANTIC_REF_TARGETS: dict[str, tuple[str, tuple[str, ...], bool]] = {
    "term": ("ontology_terms", ("term_id",), True),
    "node": ("ontology_nodes", ("node_id",), True),
    "edge": ("ontology_edges", ("edge_id",), True),
    "assertion": ("ontology_assertions", ("assertion_id",), True),
    "relation": ("relations", ("relation_id", "id"), False),
    "document": ("documents", ("id",), False),
    "page": ("documents", ("id",), False),
    "source_document": ("source_documents", ("source_document_id",), False),
    "structural_unit": ("structural_units", ("unit_id",), False),
    "evidence_atom": ("evidence_atoms", ("atom_id",), False),
    "promotion": ("document_promotions", ("promotion_id",), False),
    "field": ("extracted_fields", ("id",), False),
    "row": ("extracted_rows", ("id",), False),
    "entity": ("document_entities", ("entity_id", "id"), False),
}
