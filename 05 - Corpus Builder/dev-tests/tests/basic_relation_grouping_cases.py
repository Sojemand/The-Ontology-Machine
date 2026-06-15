from __future__ import annotations

from corpus_builder.ontology import basic_relation_mining

from .basic_relation_support import insert_document


def test_basic_relation_mining_groups_by_source_document_id_only(db):
    insert_document(db, "doc-a1", source_document_id="source-a", source_uri="first-uri.pdf", page_index=0)
    insert_document(db, "doc-a2", source_document_id="source-a", source_uri="second-uri.pdf", page_index=1)
    insert_document(db, "doc-b1", source_document_id="source-b", source_uri="first-uri.pdf", page_index=0)

    report = basic_relation_mining(db)

    assert report["status"] == "pass"
    assert report["source_documents"] == 2
    assert report["source_document_pages"] == 3
    source_a = db.execute(
        "SELECT page_count, first_document_id, last_document_id FROM source_documents WHERE source_document_id = ?",
        ("source-a",),
    ).fetchone()
    assert dict(source_a) == {"page_count": 2, "first_document_id": "doc-a1", "last_document_id": "doc-a2"}


def test_basic_relation_mining_rejects_missing_source_document_id(db):
    insert_document(db, "doc-missing", source_document_id="")

    report = basic_relation_mining(db)

    assert report["status"] == "warning"
    assert report["source_documents"] == 0
    assert report["unresolved_documents"] == [
        {"document_id": "doc-missing", "missing": ["source_document_id"], "file_name": "doc-missing.pdf"}
    ]
    assert db.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0] == 0


def test_basic_relation_mining_rejects_duplicate_page_index(db):
    insert_document(db, "doc-a1", source_document_id="source-a", page_index=0)
    insert_document(db, "doc-a1-duplicate", source_document_id="source-a", page_index=0)

    report = basic_relation_mining(db)

    assert report["status"] == "warning"
    assert report["source_documents"] == 0
    assert report["rejected_groups"] == [
        {
            "source_document_id": "source-a",
            "reason": "duplicate_page_index",
            "duplicates": {0: ["doc-a1", "doc-a1-duplicate"]},
        }
    ]
    assert db.execute("SELECT COUNT(*) FROM source_document_pages").fetchone()[0] == 0
