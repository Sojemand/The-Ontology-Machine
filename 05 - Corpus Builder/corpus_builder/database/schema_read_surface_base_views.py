"""Base read-surface view definitions."""

from __future__ import annotations

BASE_READ_SURFACE_VIEWS = (
    (
        "vw_base_evidence_atoms",
        """CREATE VIEW vw_base_evidence_atoms AS
SELECT
    atom_id,
    document_id,
    atom_type,
    json_path,
    anchor_kind,
    anchor_key,
    page,
    row_index,
    column_key,
    source_ref,
    text_value,
    normalized_text,
    compact_text,
    numeric_value,
    date_value,
    currency,
    context_label,
    context_window
FROM evidence_atoms;""",
    ),
    (
        "vw_base_slot_candidates",
        """CREATE VIEW vw_base_slot_candidates AS
SELECT
    candidate_id,
    document_id,
    slot,
    display_value,
    normalized_value,
    compact_value,
    numeric_value,
    date_value,
    strategy,
    confidence,
    ambiguity_group,
    is_projection_backed,
    candidate_layer,
    candidate_origin,
    source_refs_json,
    origin_path,
    origin_kind
FROM slot_candidates
WHERE COALESCE(candidate_layer, 'base') = 'base';""",
    ),
    (
        "vw_document_promotions_current",
        """CREATE VIEW vw_document_promotions_current AS
SELECT
    promotion_id,
    document_id,
    slot,
    slot_label,
    value_type,
    query_role,
    display_value,
    normalized_value,
    compact_value,
    numeric_value,
    date_value,
    value_json,
    ordinal,
    confidence,
    candidate_id,
    source_path,
    source_refs_json,
    projection_id,
    release_fingerprint,
    materialization_version,
    created_at
FROM document_promotions
WHERE is_current = 1;""",
    ),
    (
        "vw_document_header_surface",
        """CREATE VIEW vw_document_header_surface AS
SELECT
    d.id AS document_id,
    d.file_name,
    d.document_type,
    d.category,
    d.subcategory,
    d.language,
    d.projection_id AS document_projection_id,
    p.slot,
    p.slot_label,
    p.value_type,
    p.query_role,
    p.display_value,
    p.normalized_value,
    p.compact_value,
    p.numeric_value,
    p.date_value,
    p.ordinal,
    p.confidence,
    p.source_path,
    p.projection_id,
    p.release_fingerprint
FROM documents d
JOIN document_promotions p ON p.document_id = d.id
WHERE p.is_current = 1;""",
    ),
    (
        "vw_document_search_surface",
        """CREATE VIEW vw_document_search_surface AS
SELECT
    d.id AS document_id,
    d.file_name,
    d.document_type,
    d.category,
    d.subcategory,
    d.language,
    d.content_free_text,
    GROUP_CONCAT(p.slot || ': ' || p.display_value, ' ') AS promotion_text
FROM documents d
LEFT JOIN document_promotions p ON p.document_id = d.id AND p.is_current = 1
GROUP BY d.id;""",
    ),
    (
        "vw_observed_semantics",
        """CREATE VIEW vw_observed_semantics AS
SELECT
    'document_entity' AS subject_kind,
    de.entity_id AS subject_id,
    de.document_id,
    de.entity_id,
    NULL AS attribute_id,
    NULL AS relation_id,
    de.entity_type AS subject_type,
    de.role_type,
    NULL AS attribute_code,
    de.display_value,
    de.normalized_value,
    NULL AS numeric_value,
    NULL AS date_value,
    NULL AS value_json,
    de.source_path,
    de.state,
    NULL AS relation_type,
    NULL AS source_entity_id,
    NULL AS target_entity_id,
    NULL AS target_document_id
FROM document_entities de
WHERE COALESCE(de.state, 'materialized') = 'observed'
UNION ALL
SELECT
    'entity_attribute' AS subject_kind,
    ea.attribute_id AS subject_id,
    de.document_id,
    de.entity_id,
    ea.attribute_id,
    NULL AS relation_id,
    de.entity_type AS subject_type,
    de.role_type,
    ea.attribute_code,
    ea.display_value,
    ea.normalized_value,
    ea.numeric_value,
    ea.date_value,
    ea.value_json,
    ea.source_path,
    de.state,
    NULL AS relation_type,
    NULL AS source_entity_id,
    NULL AS target_entity_id,
    NULL AS target_document_id
FROM entity_attributes ea
JOIN document_entities de ON de.entity_id = ea.entity_id
WHERE COALESCE(de.state, 'materialized') = 'observed'
UNION ALL
SELECT
    'entity_relation' AS subject_kind,
    er.relation_id AS subject_id,
    er.document_id,
    NULL AS entity_id,
    NULL AS attribute_id,
    er.relation_id,
    er.relation_type AS subject_type,
    NULL AS role_type,
    NULL AS attribute_code,
    er.description AS display_value,
    NULL AS normalized_value,
    NULL AS numeric_value,
    NULL AS date_value,
    NULL AS value_json,
    er.source_path,
    er.status AS state,
    er.relation_type,
    er.source_entity_id,
    er.target_entity_id,
    er.target_document_id
FROM entity_relations er
WHERE COALESCE(er.status, er.relation_origin, 'observed') = 'observed'
   OR er.relation_origin = 'observed';""",
    ),
    (
        "vw_materialized_semantics",
        """CREATE VIEW vw_materialized_semantics AS
SELECT
    'document_entity' AS subject_kind,
    de.entity_id AS subject_id,
    de.document_id,
    de.entity_id,
    NULL AS attribute_id,
    NULL AS relation_id,
    de.entity_type AS subject_type,
    de.role_type,
    NULL AS attribute_code,
    de.display_value,
    de.normalized_value,
    NULL AS numeric_value,
    NULL AS date_value,
    NULL AS value_json,
    de.source_path,
    de.state,
    NULL AS relation_type,
    NULL AS source_entity_id,
    NULL AS target_entity_id,
    NULL AS target_document_id
FROM document_entities de
WHERE COALESCE(de.state, 'materialized') = 'materialized'
UNION ALL
SELECT
    'entity_attribute' AS subject_kind,
    ea.attribute_id AS subject_id,
    de.document_id,
    de.entity_id,
    ea.attribute_id,
    NULL AS relation_id,
    de.entity_type AS subject_type,
    de.role_type,
    ea.attribute_code,
    ea.display_value,
    ea.normalized_value,
    ea.numeric_value,
    ea.date_value,
    ea.value_json,
    ea.source_path,
    de.state,
    NULL AS relation_type,
    NULL AS source_entity_id,
    NULL AS target_entity_id,
    NULL AS target_document_id
FROM entity_attributes ea
JOIN document_entities de ON de.entity_id = ea.entity_id
WHERE COALESCE(de.state, 'materialized') = 'materialized'
UNION ALL
SELECT
    'entity_relation' AS subject_kind,
    er.relation_id AS subject_id,
    er.document_id,
    NULL AS entity_id,
    NULL AS attribute_id,
    er.relation_id,
    er.relation_type AS subject_type,
    NULL AS role_type,
    NULL AS attribute_code,
    er.description AS display_value,
    NULL AS normalized_value,
    NULL AS numeric_value,
    NULL AS date_value,
    NULL AS value_json,
    er.source_path,
    er.status AS state,
    er.relation_type,
    er.source_entity_id,
    er.target_entity_id,
    er.target_document_id
FROM entity_relations er
WHERE COALESCE(er.status, er.relation_origin, 'observed') = 'materialized'
   OR er.relation_origin = 'materialized';""",
    ),
)
