from __future__ import annotations

from corpus_builder.ontology import basic_relation_mining

from .basic_relation_support import insert_document


def test_basic_relation_mining_writes_page_sequence_relations(db):
    insert_document(db, "doc-a1", page_index=0, page_label="1")
    insert_document(db, "doc-a2", page_index=1, page_label="2")
    insert_document(db, "doc-a3", page_index=2, page_label="3")

    report = basic_relation_mining(db)

    assert report["status"] == "pass"
    assert report["relations_inserted"] == 7
    relation_rows = db.execute(
        "SELECT document_id, relation_type, target_hint, target_document_id, relation_origin, status, created_by "
        "FROM relations ORDER BY document_id, relation_type, target_document_id"
    ).fetchall()
    assert [dict(row) for row in relation_rows] == [
        {
            "document_id": "doc-a1",
            "relation_type": "next_page",
            "target_hint": "doc-a2",
            "target_document_id": "doc-a2",
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
        {
            "document_id": "doc-a1",
            "relation_type": "page_of_source_document",
            "target_hint": "source-a",
            "target_document_id": None,
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
        {
            "document_id": "doc-a2",
            "relation_type": "next_page",
            "target_hint": "doc-a3",
            "target_document_id": "doc-a3",
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
        {
            "document_id": "doc-a2",
            "relation_type": "page_of_source_document",
            "target_hint": "source-a",
            "target_document_id": None,
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
        {
            "document_id": "doc-a2",
            "relation_type": "previous_page",
            "target_hint": "doc-a1",
            "target_document_id": "doc-a1",
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
        {
            "document_id": "doc-a3",
            "relation_type": "page_of_source_document",
            "target_hint": "source-a",
            "target_document_id": None,
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
        {
            "document_id": "doc-a3",
            "relation_type": "previous_page",
            "target_hint": "doc-a2",
            "target_document_id": "doc-a2",
            "relation_origin": "base_graph",
            "status": "materialized",
            "created_by": "basic_relation_mining",
        },
    ]


def test_basic_relation_mining_does_not_materialize_same_source_document_pairs(db):
    insert_document(db, "doc-a1", page_index=0)
    insert_document(db, "doc-a2", page_index=1)
    insert_document(db, "doc-a3", page_index=2)

    basic_relation_mining(db)

    assert db.execute(
        "SELECT COUNT(*) FROM relations WHERE relation_type = 'same_source_document'"
    ).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM vw_same_source_document_pages").fetchone()[0] == 6
