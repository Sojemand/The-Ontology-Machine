from __future__ import annotations

from corpus_builder.ontology import basic_relation_mining

from .basic_relation_support import insert_document, insert_payload_classification


def test_basic_relation_mining_writes_source_document_classifications(db):
    for document_id, page_index, confidence in (("doc-a1", 0, 0.91), ("doc-a2", 1, 0.84)):
        insert_document(
            db,
            document_id,
            page_index=page_index,
            document_type="fiction_short_story",
            document_type_confidence=confidence,
            category="narrative_prose",
            subcategory="first_person_child_narration",
        )
    for document_id, confidence in (("doc-a1", 0.93), ("doc-a2", 0.82)):
        insert_payload_classification(
            db,
            document_id,
            document_type="fiction_short_story",
            document_type_confidence=confidence,
            category="narrative_prose",
            subcategory="first_person_child_narration",
        )

    report = basic_relation_mining(db)

    assert report["status"] == "pass"
    assert report["source_document_classifications_inserted"] == 2
    rows = db.execute(
        "SELECT classification_scope, document_type, category, subcategory, confidence, status, basis_json "
        "FROM source_document_classifications WHERE source_document_id = ? ORDER BY classification_scope",
        ("source-a",),
    ).fetchall()
    assert [
        (row["classification_scope"], row["document_type"], row["category"], row["subcategory"], row["confidence"], row["status"])
        for row in rows
    ] == [
        ("base", "fiction_short_story", "narrative_prose", "first_person_child_narration", 0.84, "materialized"),
        ("semantic_release", "fiction_short_story", "narrative_prose", "first_person_child_narration", 0.82, "materialized"),
    ]
    assert db.execute("SELECT COUNT(*) FROM vw_source_document_classifications").fetchone()[0] == 2


def test_basic_relation_mining_marks_source_classification_ambiguous_or_unresolved(db):
    insert_document(
        db,
        "doc-a1",
        source_document_id="source-a",
        page_index=0,
        document_type="fiction_short_story",
        category="narrative_prose",
        subcategory="other",
    )
    insert_document(
        db,
        "doc-a2",
        source_document_id="source-a",
        page_index=1,
        document_type="fiction_short_story",
        category="narrative_prose",
        subcategory="other",
    )
    insert_document(
        db,
        "doc-b1",
        source_document_id="source-b",
        source_uri="source-b.pdf",
        page_index=0,
        document_type="fiction_short_story",
        category="narrative_prose",
        subcategory="first_person_child_narration",
    )
    insert_document(
        db,
        "doc-b2",
        source_document_id="source-b",
        source_uri="source-b.pdf",
        page_index=1,
        document_type="fiction_short_story",
        category="narrative_prose",
        subcategory="dark_humor_revenge_tale",
    )

    report = basic_relation_mining(db)

    assert report["status"] == "pass"
    rows = db.execute(
        "SELECT source_document_id, classification_scope, document_type, category, subcategory, status, basis_json "
        "FROM source_document_classifications WHERE classification_scope = 'base' ORDER BY source_document_id",
    ).fetchall()
    assert [(row["source_document_id"], row["document_type"], row["category"], row["subcategory"], row["status"]) for row in rows] == [
        ("source-a", "fiction_short_story", "narrative_prose", None, "unresolved"),
        ("source-b", "fiction_short_story", "narrative_prose", None, "ambiguous"),
    ]
    assert "contains_other_fallback" in rows[0]["basis_json"]
    assert "conflicting_subcategory" in rows[1]["basis_json"]


def test_basic_relation_refresh_preserves_ontology_scope_classifications(db):
    insert_document(db, "doc-a1", source_document_id="source-a", page_index=0)
    first_report = basic_relation_mining(db)
    assert first_report["status"] == "pass"
    db.execute(
        "INSERT INTO ontology_lenses (ontology_id, name, description, status, intent_json, policy_json) "
        "VALUES ('lens-review', 'Review Lens', 'Keeps source-document annotations.', 'ready', '{}', '{}')"
    )
    db.execute(
        "INSERT INTO source_document_classifications (source_document_id, classification_scope, ontology_id, "
        "document_type, category, subcategory, confidence, status, basis_json, created_by) "
        "VALUES ('source-a', 'ontology', 'lens-review', 'review_note', 'needs_review', 'kept', 1.0, "
        "'materialized', '{\"basis\":\"test\"}', 'ontology_agent')"
    )
    insert_document(
        db,
        "doc-b1",
        source_document_id="source-b",
        source_uri="source-b.pdf",
        source_artifact_id="source-b.pdf",
        page_index=0,
    )

    refresh_report = basic_relation_mining(db)

    assert refresh_report["status"] == "pass"
    assert refresh_report["source_documents"] == 2
    ontology_rows = db.execute(
        "SELECT source_document_id, ontology_id, document_type, category, subcategory, created_by "
        "FROM source_document_classifications WHERE classification_scope = 'ontology'"
    ).fetchall()
    assert [dict(row) for row in ontology_rows] == [
        {
            "source_document_id": "source-a",
            "ontology_id": "lens-review",
            "document_type": "review_note",
            "category": "needs_review",
            "subcategory": "kept",
            "created_by": "ontology_agent",
        }
    ]
    assert db.execute("SELECT COUNT(*) FROM source_document_pages").fetchone()[0] == 2
