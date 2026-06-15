from __future__ import annotations

from corpus_builder.database import get_schema_description


def test_documents_schema_has_no_legacy_columns(db):
    columns = {row["name"] for row in db.execute("PRAGMA table_info(documents)").fetchall()}

    assert "project_code" not in columns
    assert "payment_terms" not in columns
    assert "overtime_hours" not in columns
    assert "net_salary" not in columns
    assert "document_type_confidence" in columns
    assert "source_file_path" in columns
    assert "source_page" in columns
    assert "source_page_count" in columns
    assert "source_document_id" in columns
    assert "source_uri" in columns
    assert "source_artifact_id" in columns
    assert "ingest_run_id" in columns
    assert "page_index" in columns
    assert "materialization_order" in columns
    assert "page_content_hash" in columns
    assert "source_content_hash" in columns
    assert "validator_status" in columns
    assert "interpreter_needs_review" in columns
    assert "interpreter_review_reason" in columns
    assert "normalizer_needs_review" in columns
    assert "normalizer_review_reason" in columns


def test_dynamic_document_promotions_schema_and_views_exist(db):
    promotion_columns = {row["name"] for row in db.execute("PRAGMA table_info(document_promotions)").fetchall()}
    views = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall()}

    assert {"slot", "slot_label", "query_role", "display_value", "candidate_id", "is_current"} <= promotion_columns
    assert "vw_document_promotions_current" in views
    assert "vw_document_header_surface" in views
    assert "vw_document_search_surface" in views


def test_ontology_schema_and_read_surface_exist(db):
    tables = {
        row["name"]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    views = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall()}

    assert {
        "source_documents",
        "source_document_pages",
        "source_document_classifications",
        "ontology_lenses",
        "ontology_runs",
        "ontology_nodes",
        "ontology_edges",
        "ontology_assertions",
        "ontology_evidence_links",
        "ontology_activation",
        "ontology_embedding_chunks",
        "ontology_edit_log",
    } <= tables
    assert {
        "vw_source_document_surface",
        "vw_source_document_classifications",
        "vw_same_source_document_pages",
        "vw_active_ontology_nodes",
        "vw_active_ontology_edges",
        "vw_active_ontology_assertions",
        "vw_query_surface_with_active_ontology",
    } <= views


def test_ontology_text_primary_keys_are_explicitly_not_null(db):
    required_ids = {
        "source_documents": "source_document_id",
        "ontology_lenses": "ontology_id",
        "ontology_runs": "run_id",
        "ontology_terms": "term_id",
        "ontology_nodes": "node_id",
        "ontology_edges": "edge_id",
        "ontology_assertions": "assertion_id",
        "ontology_evidence_links": "evidence_link_id",
        "ontology_embedding_chunks": "chunk_id",
        "ontology_edit_log": "edit_id",
    }

    for table_name, column_name in required_ids.items():
        columns = {row["name"]: row for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
        assert columns[column_name]["notnull"] == 1


def test_schema_description_mentions_core_tables(db):
    description = get_schema_description(db)

    assert "documents" in description
    assert "extracted_fields" in description
    assert "extracted_rows" in description
    assert "normalisierte" in description


def test_search_schema_creates_embedding_chunks_table(db):
    tables = {
        row["name"]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }

    assert "embedding_chunks" in tables
