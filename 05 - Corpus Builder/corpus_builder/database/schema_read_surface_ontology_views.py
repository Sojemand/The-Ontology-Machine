"""Ontology read-surface view definitions."""

from __future__ import annotations

ONTOLOGY_READ_SURFACE_VIEWS = (
    (
        "vw_active_ontology_nodes",
        """CREATE VIEW vw_active_ontology_nodes AS
SELECT
    l.ontology_id,
    l.name AS ontology_name,
    n.node_id,
    n.node_type,
    n.canonical_label,
    n.source_ref_type,
    n.source_ref_id,
    n.summary,
    n.attributes_json,
    n.confidence,
    n.status,
    l.embedding_status
FROM ontology_activation a
JOIN ontology_lenses l ON l.ontology_id = a.ontology_id
JOIN ontology_nodes n ON n.ontology_id = l.ontology_id
WHERE a.scope = 'corpus'
  AND a.scope_ref = 'self'
  AND a.is_active = 1
  AND a.is_primary = 1
  AND l.status = 'ready';""",
    ),
    (
        "vw_active_ontology_edges",
        """CREATE VIEW vw_active_ontology_edges AS
SELECT
    l.ontology_id,
    l.name AS ontology_name,
    e.edge_id,
    e.source_node_id,
    source_node.canonical_label AS source_label,
    e.target_node_id,
    target_node.canonical_label AS target_label,
    e.relation_type,
    e.relation_label,
    e.attributes_json,
    e.confidence,
    e.status,
    COUNT(ev.evidence_link_id) AS evidence_count
FROM ontology_activation a
JOIN ontology_lenses l ON l.ontology_id = a.ontology_id
JOIN ontology_edges e ON e.ontology_id = l.ontology_id
JOIN ontology_nodes source_node ON source_node.node_id = e.source_node_id
JOIN ontology_nodes target_node ON target_node.node_id = e.target_node_id
LEFT JOIN ontology_evidence_links ev
  ON ev.ontology_id = e.ontology_id
 AND ev.target_type = 'edge'
 AND ev.target_id = e.edge_id
WHERE a.scope = 'corpus'
  AND a.scope_ref = 'self'
  AND a.is_active = 1
  AND a.is_primary = 1
  AND l.status = 'ready'
GROUP BY
    l.ontology_id, l.name, e.edge_id, e.source_node_id, source_node.canonical_label,
    e.target_node_id, target_node.canonical_label, e.relation_type, e.relation_label,
    e.attributes_json, e.confidence, e.status;""",
    ),
    (
        "vw_active_ontology_assertions",
        """CREATE VIEW vw_active_ontology_assertions AS
SELECT
    l.ontology_id,
    l.name AS ontology_name,
    ass.assertion_id,
    ass.subject_ref_type,
    ass.subject_ref_id,
    ass.predicate,
    ass.object_ref_type,
    ass.object_ref_id,
    ass.value_text,
    ass.confidence,
    ass.status,
    COUNT(ev.evidence_link_id) AS evidence_count
FROM ontology_activation a
JOIN ontology_lenses l ON l.ontology_id = a.ontology_id
JOIN ontology_assertions ass ON ass.ontology_id = l.ontology_id
LEFT JOIN ontology_evidence_links ev
  ON ev.ontology_id = ass.ontology_id
 AND ev.target_type = 'assertion'
 AND ev.target_id = ass.assertion_id
WHERE a.scope = 'corpus'
  AND a.scope_ref = 'self'
  AND a.is_active = 1
  AND a.is_primary = 1
  AND l.status = 'ready'
GROUP BY
    l.ontology_id, l.name, ass.assertion_id, ass.subject_ref_type, ass.subject_ref_id,
    ass.predicate, ass.object_ref_type, ass.object_ref_id, ass.value_text,
    ass.confidence, ass.status;""",
    ),
    (
        "vw_query_surface_with_active_ontology",
        """CREATE VIEW vw_query_surface_with_active_ontology AS
SELECT
    'source_document' AS surface_type,
    s.source_document_id AS surface_id,
    NULL AS ontology_id,
    s.source_document_id,
    NULL AS document_id,
    COALESCE(s.source_title, s.source_uri) AS label,
    NULL AS body_text,
    'source_document' AS source_ref_type,
    s.source_document_id AS source_ref_id,
    'materialized' AS status,
    1.0 AS confidence,
    NULL AS embedding_status,
    json_object(
        'source_uri', s.source_uri,
        'source_kind', s.source_kind,
        'page_count', s.page_count,
        'base_document_type', s.base_document_type,
        'base_category', s.base_category,
        'base_subcategory', s.base_subcategory,
        'base_classification_status', s.base_classification_status,
        'semantic_release_document_type', s.semantic_release_document_type,
        'semantic_release_category', s.semantic_release_category,
        'semantic_release_subcategory', s.semantic_release_subcategory,
        'semantic_release_classification_status', s.semantic_release_classification_status,
        'entity_count', s.entity_count,
        'evidence_atom_count', s.evidence_atom_count,
        'promotion_count', s.promotion_count
    ) AS metadata_json
FROM vw_source_document_surface s
UNION ALL
SELECT
    'structural_unit' AS surface_type,
    unit.unit_id AS surface_id,
    NULL AS ontology_id,
    unit.source_document_id,
    unit.document_id,
    COALESCE(unit.label, unit.unit_type) AS label,
    NULL AS body_text,
    'structural_unit' AS source_ref_type,
    unit.unit_id AS source_ref_id,
    unit.status,
    unit.confidence,
    NULL AS embedding_status,
    unit.metadata_json
FROM vw_structural_units unit
UNION ALL
SELECT
    'ontology_node' AS surface_type,
    n.node_id AS surface_id,
    n.ontology_id,
    CASE
        WHEN n.source_ref_type = 'source_document' THEN n.source_ref_id
        WHEN n.source_ref_type = 'structural_unit' THEN node_unit.source_document_id
        ELSE NULL
    END AS source_document_id,
    CASE
        WHEN n.source_ref_type = 'document' THEN n.source_ref_id
        WHEN n.source_ref_type = 'structural_unit' THEN node_unit.document_id
        ELSE NULL
    END AS document_id,
    n.canonical_label AS label,
    n.summary AS body_text,
    n.source_ref_type,
    n.source_ref_id,
    n.status,
    n.confidence,
    n.embedding_status,
    n.attributes_json AS metadata_json
FROM vw_active_ontology_nodes n
LEFT JOIN structural_units node_unit
  ON n.source_ref_type = 'structural_unit'
 AND node_unit.unit_id = n.source_ref_id
UNION ALL
SELECT
    'ontology_edge' AS surface_type,
    e.edge_id AS surface_id,
    e.ontology_id,
    NULL AS source_document_id,
    NULL AS document_id,
    COALESCE(e.relation_label, e.relation_type) AS label,
    e.source_label || ' -> ' || e.target_label AS body_text,
    'ontology_edge' AS source_ref_type,
    e.edge_id AS source_ref_id,
    e.status,
    e.confidence,
    NULL AS embedding_status,
    e.attributes_json AS metadata_json
FROM vw_active_ontology_edges e
UNION ALL
SELECT
    'ontology_assertion' AS surface_type,
    a.assertion_id AS surface_id,
    a.ontology_id,
    CASE
        WHEN a.subject_ref_type = 'source_document' THEN a.subject_ref_id
        WHEN a.subject_ref_type = 'structural_unit' THEN assertion_unit.source_document_id
        ELSE NULL
    END AS source_document_id,
    CASE
        WHEN a.subject_ref_type = 'document' THEN a.subject_ref_id
        WHEN a.subject_ref_type = 'structural_unit' THEN assertion_unit.document_id
        ELSE NULL
    END AS document_id,
    a.predicate AS label,
    a.value_text AS body_text,
    a.subject_ref_type AS source_ref_type,
    a.subject_ref_id AS source_ref_id,
    a.status,
    a.confidence,
    NULL AS embedding_status,
    json_object(
        'object_ref_type', a.object_ref_type,
        'object_ref_id', a.object_ref_id,
        'evidence_count', a.evidence_count
    ) AS metadata_json
FROM vw_active_ontology_assertions a
LEFT JOIN structural_units assertion_unit
  ON a.subject_ref_type = 'structural_unit'
 AND assertion_unit.unit_id = a.subject_ref_id;""",
    ),
)
