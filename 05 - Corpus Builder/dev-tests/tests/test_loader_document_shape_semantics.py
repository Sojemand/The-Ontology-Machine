from __future__ import annotations

import json

from tests.fixtures.loader_io import load_input_file

def test_load_from_file_mixed_sidecar_keeps_dynamic_content_surfaces(db, mixed_structured, legacy_validation_report, make_input_pair):
    json_path = make_input_pair("mixed_budget", mixed_structured, legacy_report=legacy_validation_report)

    result = load_input_file(db, json_path)

    assert result.status == "loaded"
    row = db.execute(
        "SELECT validator_status, needs_review, content_fields_json, content_rows_json, content_free_text FROM documents WHERE id = ?",
        ("mixed_budget",),
    ).fetchone()
    assert row["validator_status"] == "warn"
    assert row["needs_review"] == 1
    fields_json = json.loads(row["content_fields_json"])
    rows_json = json.loads(row["content_rows_json"])
    assert fields_json["invoice_number"] == "BUD-2024-01"
    assert sum(row["amount"] for row in rows_json) == 1200.5
    assert row["content_free_text"] is None
    org = db.execute(
        "SELECT normalized_name, compact_name FROM organizations WHERE document_id = ? AND name = ?",
        ("mixed_budget", "KGV Abendrot e.V."),
    ).fetchone()
    assert org["normalized_name"] == "kgv abendrot e v"
    assert org["compact_name"] == "kgvabendrotev"

def test_load_from_file_persists_observed_segments_and_segment_relations(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    structured = dict(vision_structured)
    structured["content"] = dict(vision_structured["content"])
    structured["content"]["segments"] = [
        {
            "segment_id": "seg_001",
            "unit_kind": "question",
            "page": 1,
            "sequence": 1,
            "section": "Generelle Fragen",
            "label": "Kann die Anlage betrieben werden?",
            "text": "Kann die Anlage betrieben werden?",
            "_source_refs": {"text": ["page1_para_1"]},
        },
        {
            "segment_id": "seg_002",
            "unit_kind": "description",
            "function": "answer_statement",
            "page": 1,
            "sequence": 2,
            "text": "Die Anlage kann betrieben werden.",
            "attributes": {"certainty": "hoch"},
            "_source_refs": {"text": ["page1_para_2"]},
        },
    ]
    structured["relations"] = [
        {
            "type": "elaborates",
            "source_id": "seg_002",
            "target_id": "seg_001",
            "confidence": 0.83,
        }
    ]

    json_path = make_input_pair("segment_doc", structured, vision_report=vision_validation_report)
    result = load_input_file(db, json_path)

    assert result.status == "loaded"
    entity = db.execute(
        "SELECT entity_key, entity_type, role_type, source_path, page, sequence, state FROM document_entities WHERE document_id = ? AND entity_key = ?",
        ("segment_doc", "segment:seg_001"),
    ).fetchone()
    assert entity["entity_type"] == "segment"
    assert entity["role_type"] == "question"
    assert entity["source_path"] == "content.segments[0]"
    assert entity["page"] == 1
    assert entity["sequence"] == 1
    assert entity["state"] == "observed"

    attribute = db.execute(
        "SELECT ea.attribute_code, ea.display_value FROM entity_attributes ea JOIN document_entities de ON de.entity_id = ea.entity_id WHERE de.document_id = ? AND de.entity_key = ? AND ea.attribute_code = ?",
        ("segment_doc", "segment:seg_002", "certainty"),
    ).fetchone()
    assert attribute["display_value"] == "hoch"

    function_attr = db.execute(
        "SELECT ea.attribute_code, ea.display_value FROM entity_attributes ea JOIN document_entities de ON de.entity_id = ea.entity_id WHERE de.document_id = ? AND de.entity_key = ? AND ea.attribute_code = ?",
        ("segment_doc", "segment:seg_002", "function"),
    ).fetchone()
    assert function_attr["display_value"] == "answer_statement"
    source_refs_attr = db.execute(
        "SELECT ea.attribute_code FROM entity_attributes ea JOIN document_entities de ON de.entity_id = ea.entity_id WHERE de.document_id = ? AND de.entity_key = ? AND ea.attribute_code = ?",
        ("segment_doc", "segment:seg_002", "source_refs"),
    ).fetchone()
    assert source_refs_attr is None

    relation = db.execute(
        "SELECT relation_type, relation_origin, status, created_by FROM entity_relations WHERE document_id = ?",
        ("segment_doc",),
    ).fetchone()
    assert relation["relation_type"] == "elaborates"
    assert relation["relation_origin"] == "observed"
    assert relation["status"] == "observed"
    assert relation["created_by"] == "corpus_builder"

    atom = db.execute(
        "SELECT atom_type, source_ref, text_value, anchor_kind, anchor_key FROM evidence_atoms WHERE document_id = ? AND json_path = ?",
        ("segment_doc", "content.segments[0].text"),
    ).fetchone()
    assert atom["atom_type"] == "segment"
    assert atom["source_ref"] == "page1_para_1"
    assert atom["text_value"] == "Kann die Anlage betrieben werden?"
    assert atom["anchor_kind"] == "segment"
    assert atom["anchor_key"] == "segment:seg_001"

    assert db.execute(
        "SELECT COUNT(*) FROM semantic_evidence_links sel "
        "JOIN document_entities de ON de.entity_id = sel.subject_id AND sel.subject_kind = 'document_entity' "
        "JOIN evidence_atoms atom ON atom.atom_id = sel.atom_id "
        "WHERE de.document_id = ? AND de.entity_key = ? AND atom.json_path = ?",
        ("segment_doc", "segment:seg_001", "content.segments[0].text"),
    ).fetchone()[0] >= 1
    assert db.execute(
        "SELECT COUNT(*) FROM semantic_evidence_links sel "
        "JOIN entity_attributes ea ON ea.attribute_id = sel.subject_id AND sel.subject_kind = 'entity_attribute' "
        "JOIN document_entities de ON de.entity_id = ea.entity_id "
        "JOIN evidence_atoms atom ON atom.atom_id = sel.atom_id "
        "WHERE de.document_id = ? AND de.entity_key = ? AND ea.attribute_code = ? AND atom.json_path = ?",
        ("segment_doc", "segment:seg_002", "certainty", "content.segments[1].attributes.certainty"),
    ).fetchone()[0] >= 1
    assert db.execute(
        "SELECT COUNT(*) FROM semantic_evidence_links sel "
        "JOIN entity_relations er ON er.relation_id = sel.subject_id AND sel.subject_kind = 'entity_relation' "
        "WHERE er.document_id = ? AND er.relation_type = ?",
        ("segment_doc", "elaborates"),
    ).fetchone()[0] >= 1
    assert db.execute(
        "SELECT COUNT(*) FROM vw_observed_semantics WHERE document_id = ? AND subject_kind = ?",
        ("segment_doc", "document_entity"),
    ).fetchone()[0] == 2
