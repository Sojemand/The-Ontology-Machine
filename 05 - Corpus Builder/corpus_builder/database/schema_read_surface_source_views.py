"""Source-document read-surface view definitions."""

from __future__ import annotations

SOURCE_READ_SURFACE_VIEWS = (
    (
        "vw_source_document_pages",
        """CREATE VIEW vw_source_document_pages AS
SELECT
    sdp.source_document_id,
    sd.source_uri,
    sd.source_title,
    sd.source_kind,
    sd.page_count,
    sdp.document_id,
    sdp.page_index,
    sdp.page_label,
    sdp.prev_document_id,
    sdp.next_document_id,
    d.content_hash,
    d.materialization_order
FROM source_document_pages sdp
JOIN source_documents sd ON sd.source_document_id = sdp.source_document_id
JOIN documents d ON d.id = sdp.document_id;""",
    ),
    (
        "vw_source_document_classifications",
        """CREATE VIEW vw_source_document_classifications AS
SELECT
    cls.source_document_id,
    sd.source_uri,
    sd.source_title,
    cls.classification_scope,
    cls.ontology_id,
    cls.document_type,
    cls.category,
    cls.subcategory,
    cls.confidence,
    cls.status,
    cls.created_by,
    cls.updated_at,
    cls.basis_json
FROM source_document_classifications cls
JOIN source_documents sd ON sd.source_document_id = cls.source_document_id;""",
    ),
    (
        "vw_source_document_surface",
        """CREATE VIEW vw_source_document_surface AS
SELECT
    sd.source_document_id,
    sd.source_uri,
    sd.source_title,
    sd.source_kind,
    sd.page_count,
    sd.first_document_id,
    sd.last_document_id,
    MIN(sdp.page_index) AS first_page_index,
    MAX(sdp.page_index) AS last_page_index,
    base_cls.document_type AS base_document_type,
    base_cls.category AS base_category,
    base_cls.subcategory AS base_subcategory,
    base_cls.status AS base_classification_status,
    release_cls.document_type AS semantic_release_document_type,
    release_cls.category AS semantic_release_category,
    release_cls.subcategory AS semantic_release_subcategory,
    release_cls.status AS semantic_release_classification_status,
    COUNT(DISTINCT de.entity_id) AS entity_count,
    COUNT(DISTINCT ea.atom_id) AS evidence_atom_count,
    COUNT(DISTINCT dp.promotion_id) AS promotion_count
FROM source_documents sd
JOIN source_document_pages sdp ON sdp.source_document_id = sd.source_document_id
LEFT JOIN source_document_classifications base_cls
  ON base_cls.source_document_id = sd.source_document_id
 AND base_cls.classification_scope = 'base'
 AND base_cls.ontology_id IS NULL
LEFT JOIN source_document_classifications release_cls
  ON release_cls.source_document_id = sd.source_document_id
 AND release_cls.classification_scope = 'semantic_release'
 AND release_cls.ontology_id IS NULL
LEFT JOIN document_entities de ON de.document_id = sdp.document_id
LEFT JOIN evidence_atoms ea ON ea.document_id = sdp.document_id
LEFT JOIN document_promotions dp ON dp.document_id = sdp.document_id AND COALESCE(dp.is_current, 1) = 1
GROUP BY
    sd.source_document_id,
    sd.source_uri,
    sd.source_title,
    sd.source_kind,
    sd.page_count,
    sd.first_document_id,
    sd.last_document_id,
    base_cls.document_type,
    base_cls.category,
    base_cls.subcategory,
    base_cls.status,
    release_cls.document_type,
    release_cls.category,
    release_cls.subcategory,
    release_cls.status;""",
    ),
    (
        "vw_same_source_document_pages",
        """CREATE VIEW vw_same_source_document_pages AS
SELECT
    left_page.source_document_id,
    left_page.document_id AS left_document_id,
    left_page.page_index AS left_page_index,
    right_page.document_id AS right_document_id,
    right_page.page_index AS right_page_index
FROM source_document_pages left_page
JOIN source_document_pages right_page
  ON right_page.source_document_id = left_page.source_document_id
 AND right_page.document_id <> left_page.document_id;""",
    ),
    (
        "vw_structural_units",
        """CREATE VIEW vw_structural_units AS
SELECT
    unit.unit_id,
    unit.source_document_id,
    unit.unit_type,
    unit.parent_unit_id,
    unit.document_id,
    unit.page_index,
    unit.page_label,
    unit.ordinal,
    unit.start_page_index,
    unit.end_page_index,
    unit.start_char,
    unit.end_char,
    unit.label,
    unit.text_hash,
    unit.unit_origin,
    unit.confidence,
    unit.status,
    sd.source_title,
    sd.source_uri,
    sd.page_count,
    d.file_name,
    d.document_type,
    unit.metadata_json
FROM structural_units unit
JOIN source_documents sd ON sd.source_document_id = unit.source_document_id
LEFT JOIN documents d ON d.id = unit.document_id;""",
    ),
    (
        "vw_structural_unit_relations",
        """CREATE VIEW vw_structural_unit_relations AS
SELECT
    rel.relation_id,
    rel.source_document_id,
    rel.source_unit_id,
    source_unit.unit_type AS source_unit_type,
    rel.target_unit_id,
    target_unit.unit_type AS target_unit_type,
    rel.relation_type,
    rel.ordinal,
    rel.relation_origin,
    rel.confidence,
    rel.status,
    rel.evidence_json
FROM structural_unit_relations rel
JOIN structural_units source_unit ON source_unit.unit_id = rel.source_unit_id
JOIN structural_units target_unit ON target_unit.unit_id = rel.target_unit_id;""",
    ),
    (
        "vw_source_document_entities",
        """CREATE VIEW vw_source_document_entities AS
SELECT
    sdp.source_document_id,
    sdp.document_id,
    sdp.page_index,
    de.entity_id,
    de.entity_key,
    de.entity_type,
    de.role_type,
    de.display_value,
    de.normalized_value,
    de.source_path,
    de.row_index,
    de.sequence,
    de.state
FROM source_document_pages sdp
JOIN document_entities de ON de.document_id = sdp.document_id;""",
    ),
    (
        "vw_source_document_evidence_atoms",
        """CREATE VIEW vw_source_document_evidence_atoms AS
SELECT
    sdp.source_document_id,
    sdp.document_id,
    sdp.page_index,
    ea.atom_id,
    ea.atom_type,
    ea.json_path,
    ea.anchor_kind,
    ea.anchor_key,
    ea.row_index,
    ea.column_key,
    ea.text_value,
    ea.normalized_text,
    ea.compact_text,
    ea.numeric_value,
    ea.date_value,
    ea.currency,
    ea.context_label,
    ea.context_window
FROM source_document_pages sdp
JOIN evidence_atoms ea ON ea.document_id = sdp.document_id;""",
    ),
    (
        "vw_source_document_promotions",
        """CREATE VIEW vw_source_document_promotions AS
SELECT
    sdp.source_document_id,
    sdp.document_id,
    sdp.page_index,
    dp.promotion_id,
    dp.slot,
    dp.slot_label,
    dp.value_type,
    dp.query_role,
    dp.display_value,
    dp.normalized_value,
    dp.compact_value,
    dp.numeric_value,
    dp.date_value,
    dp.value_json,
    dp.ordinal,
    dp.confidence,
    dp.source_refs_json,
    dp.is_current
FROM source_document_pages sdp
JOIN document_promotions dp
  ON dp.document_id = sdp.document_id
 AND COALESCE(dp.is_current, 1) = 1;""",
    ),
)
