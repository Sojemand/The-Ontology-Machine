from __future__ import annotations

from corpus_builder.ontology import basic_relation_mining

from .basic_relation_support import insert_document


def test_basic_relation_mining_writes_structural_units(db):
    insert_document(db, "doc-a1", page_index=0, page_label="1")
    insert_document(db, "doc-a2", page_index=1, page_label="2")
    insert_document(db, "doc-a3", page_index=2, page_label="3")

    report = basic_relation_mining(db)

    assert report["status"] == "pass"
    assert report["structural_units_inserted"] == 4
    assert report["structural_unit_relations_inserted"] == 7
    unit_counts = db.execute(
        "SELECT unit_type, COUNT(*) AS count FROM structural_units GROUP BY unit_type ORDER BY unit_type"
    ).fetchall()
    assert [dict(row) for row in unit_counts] == [
        {"unit_type": "base_unit", "count": 1},
        {"unit_type": "page_unit", "count": 3},
    ]
    relation_counts = db.execute(
        "SELECT relation_type, COUNT(*) AS count FROM structural_unit_relations GROUP BY relation_type ORDER BY relation_type"
    ).fetchall()
    assert [dict(row) for row in relation_counts] == [
        {"relation_type": "contains", "count": 3},
        {"relation_type": "next", "count": 2},
        {"relation_type": "previous", "count": 2},
    ]
    page_units = db.execute(
        "SELECT document_id, page_index, parent_unit_id FROM structural_units WHERE unit_type = 'page_unit' ORDER BY page_index"
    ).fetchall()
    assert [row["document_id"] for row in page_units] == ["doc-a1", "doc-a2", "doc-a3"]
    assert all(row["parent_unit_id"] for row in page_units)
