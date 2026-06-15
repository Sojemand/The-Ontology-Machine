"""Deterministic structural segmentation schema contracts for corpus.db."""

from __future__ import annotations

from .types import IndexContract, TableContract

STRUCTURE_TABLES = (
    TableContract(
        "structural_units",
        """CREATE TABLE IF NOT EXISTS structural_units (
    unit_id TEXT PRIMARY KEY NOT NULL,
    source_document_id TEXT NOT NULL,
    unit_type TEXT NOT NULL CHECK (unit_type IN ('base_unit', 'chapter', 'section', 'page_unit', 'page_span')),
    parent_unit_id TEXT,
    document_id TEXT,
    page_index INTEGER,
    page_label TEXT,
    ordinal INTEGER NOT NULL DEFAULT 0 CHECK (ordinal >= 0),
    start_page_index INTEGER,
    end_page_index INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    label TEXT,
    text_hash TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    unit_origin TEXT NOT NULL DEFAULT 'base_graph',
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL DEFAULT 'materialized' CHECK (status IN ('materialized', 'draft', 'verified', 'rejected', 'deprecated')),
    created_by TEXT NOT NULL DEFAULT 'basic_relation_mining',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (source_document_id) REFERENCES source_documents(source_document_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_unit_id) REFERENCES structural_units(unit_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "structural_units stores deterministic source-document, page and future segment units.",
    ),
    TableContract(
        "structural_unit_relations",
        """CREATE TABLE IF NOT EXISTS structural_unit_relations (
    relation_id TEXT PRIMARY KEY NOT NULL,
    source_document_id TEXT NOT NULL,
    source_unit_id TEXT NOT NULL,
    target_unit_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('contains', 'next', 'previous')),
    ordinal INTEGER NOT NULL DEFAULT 0 CHECK (ordinal >= 0),
    relation_origin TEXT NOT NULL DEFAULT 'base_graph',
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'materialized' CHECK (status IN ('materialized', 'draft', 'verified', 'rejected', 'deprecated')),
    created_by TEXT NOT NULL DEFAULT 'basic_relation_mining',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (source_document_id) REFERENCES source_documents(source_document_id) ON DELETE CASCADE,
    FOREIGN KEY (source_unit_id) REFERENCES structural_units(unit_id) ON DELETE CASCADE,
    FOREIGN KEY (target_unit_id) REFERENCES structural_units(unit_id) ON DELETE CASCADE
);""",
        "structural_unit_relations connects structural units without overloading document relations.",
    ),
)

STRUCTURE_INDEXES = (
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_units_source_document ON structural_units(source_document_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_units_type ON structural_units(unit_type);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_units_parent ON structural_units(parent_unit_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_units_document ON structural_units(document_id);"),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_structural_units_source_parent_type_order "
        "ON structural_units(source_document_id, COALESCE(parent_unit_id, ''), unit_type, ordinal);"
    ),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_unit_rel_source ON structural_unit_relations(source_unit_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_unit_rel_target ON structural_unit_relations(target_unit_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_structural_unit_rel_source_document ON structural_unit_relations(source_document_id);"),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_structural_unit_rel_pair "
        "ON structural_unit_relations(source_unit_id, target_unit_id, relation_type);"
    ),
)

__all__ = ["STRUCTURE_INDEXES", "STRUCTURE_TABLES"]
