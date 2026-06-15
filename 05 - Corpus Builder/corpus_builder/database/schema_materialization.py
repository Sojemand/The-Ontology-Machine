"""Release, materialization, and audit contract for semantic corpus.db stages."""

from __future__ import annotations

from .types import IndexContract, TableContract

MATERIALIZATION_TABLES = (
    TableContract(
        "installation_state",
        """CREATE TABLE IF NOT EXISTS installation_state (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version TEXT NOT NULL,
    active_snapshot_id TEXT,
    active_release_id TEXT,
    active_release_version TEXT,
    active_release_fingerprint TEXT,
    master_taxonomy_id TEXT,
    master_taxonomy_version TEXT,
    master_taxonomy_release_id TEXT,
    runtime_locale TEXT,
    integrity_status TEXT,
    materialization_version TEXT,
    updated_at TEXT NOT NULL
);""",
        "installation_state fixiert den aktiven Semantic Release fuer genau dieses Corpus.",
    ),
    TableContract(
        "semantic_snapshots",
        """CREATE TABLE IF NOT EXISTS semantic_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    release_json TEXT NOT NULL,
    master_taxonomy_release_id TEXT NOT NULL,
    runtime_locale TEXT,
    release_id TEXT NOT NULL,
    release_version TEXT NOT NULL,
    release_fingerprint TEXT NOT NULL,
    release_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);""",
        "semantic_snapshots speichert die eingebettete Runtime-Wahrheit pro aktivierbarem Semantic Release.",
    ),
    TableContract(
        "document_processing_state",
        """CREATE TABLE IF NOT EXISTS document_processing_state (
    document_id TEXT PRIMARY KEY,
    schema_version TEXT,
    materialization_version TEXT,
    materialized_snapshot_id TEXT,
    projection_id TEXT,
    projection_fingerprint TEXT,
    materialization_state TEXT NOT NULL DEFAULT 'legacy',
    stale_reason TEXT,
    source_mode TEXT NOT NULL DEFAULT 'structured',
    last_materialized_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "document_processing_state trennt Dokumentkopf von semantischem Materialisierungszustand.",
    ),
    TableContract(
        "document_entities",
        """CREATE TABLE IF NOT EXISTS document_entities (
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    role_type TEXT,
    display_value TEXT,
    normalized_value TEXT,
    source_path TEXT,
    row_index INTEGER,
    page INTEGER,
    sequence INTEGER,
    projection_id TEXT,
    materialization_version TEXT,
    state TEXT NOT NULL DEFAULT 'materialized',
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "document_entities materialisiert semantische Entitaeten pro Dokument und Release.",
    ),
    TableContract(
        "entity_attributes",
        """CREATE TABLE IF NOT EXISTS entity_attributes (
    attribute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    attribute_code TEXT NOT NULL,
    display_value TEXT,
    normalized_value TEXT,
    numeric_value REAL,
    date_value TEXT,
    value_json TEXT,
    source_path TEXT,
    FOREIGN KEY (entity_id) REFERENCES document_entities(entity_id) ON DELETE CASCADE
);""",
        "entity_attributes speichert attributierte Werte fuer materialisierte Entitaeten.",
    ),
    TableContract(
        "entity_relations",
        """CREATE TABLE IF NOT EXISTS entity_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    source_entity_id INTEGER,
    target_entity_id INTEGER,
    target_document_id TEXT,
    target_hint TEXT,
    description TEXT,
    source_path TEXT,
    relation_origin TEXT NOT NULL DEFAULT 'observed',
    confidence REAL,
    evidence_refs TEXT,
    inference_policy_version TEXT,
    status TEXT NOT NULL DEFAULT 'observed',
    created_by TEXT NOT NULL DEFAULT 'corpus_builder',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (source_entity_id) REFERENCES document_entities(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES document_entities(entity_id) ON DELETE CASCADE
);""",
        "entity_relations haelt semantische Beziehungsgraphen und optionale Dokumentziele.",
    ),
    TableContract(
        "semantic_evidence_links",
        """CREATE TABLE IF NOT EXISTS semantic_evidence_links (
    subject_kind TEXT NOT NULL,
    subject_id INTEGER NOT NULL,
    atom_id INTEGER NOT NULL,
    evidence_role TEXT NOT NULL DEFAULT 'source',
    PRIMARY KEY (subject_kind, subject_id, atom_id, evidence_role),
    FOREIGN KEY (atom_id) REFERENCES evidence_atoms(atom_id) ON DELETE CASCADE
);""",
        "semantic_evidence_links verbindet semantische Subjekte direkt mit Evidence-Atoms.",
    ),
    TableContract(
        "materialization_runs",
        """CREATE TABLE IF NOT EXISTS materialization_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    release_version TEXT,
    scope TEXT,
    processed_count INTEGER DEFAULT 0,
    stale_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    notes TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);""",
        "materialization_runs dokumentiert Backfill- und Release-Laeufe fuer Audit und Debugging.",
    ),
    TableContract(
        "materialization_audit",
        """CREATE TABLE IF NOT EXISTS materialization_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    level TEXT NOT NULL,
    code TEXT NOT NULL,
    document_id TEXT,
    projection_id TEXT,
    message TEXT NOT NULL,
    details_json TEXT
);""",
        "materialization_audit speichert Audit-Spuren fuer Release- und Materialisierungsfehler.",
    ),
)

MATERIALIZATION_INDEXES = tuple(
    IndexContract(sql)
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_processing_state_projection ON document_processing_state(projection_id);",
        "CREATE INDEX IF NOT EXISTS idx_processing_state_state ON document_processing_state(materialization_state);",
        "CREATE INDEX IF NOT EXISTS idx_processing_state_snapshot ON document_processing_state(materialized_snapshot_id);",
        "CREATE INDEX IF NOT EXISTS idx_semantic_snapshots_master_line ON semantic_snapshots(master_taxonomy_release_id);",
        "CREATE INDEX IF NOT EXISTS idx_semantic_snapshots_release ON semantic_snapshots(release_id, release_version);",
        "CREATE INDEX IF NOT EXISTS idx_entities_document ON document_entities(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_entities_type ON document_entities(entity_type);",
        "CREATE INDEX IF NOT EXISTS idx_entities_role ON document_entities(role_type);",
        "CREATE INDEX IF NOT EXISTS idx_entities_projection ON document_entities(projection_id);",
        "CREATE INDEX IF NOT EXISTS idx_entity_attributes_entity ON entity_attributes(entity_id);",
        "CREATE INDEX IF NOT EXISTS idx_entity_attributes_code ON entity_attributes(attribute_code);",
        "CREATE INDEX IF NOT EXISTS idx_entity_attributes_normalized ON entity_attributes(normalized_value);",
        "CREATE INDEX IF NOT EXISTS idx_entity_relations_document ON entity_relations(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_entity_relations_type ON entity_relations(relation_type);",
        "CREATE INDEX IF NOT EXISTS idx_entity_relations_origin ON entity_relations(relation_origin);",
        "CREATE INDEX IF NOT EXISTS idx_entity_relations_status ON entity_relations(status);",
        "CREATE INDEX IF NOT EXISTS idx_semantic_evidence_subject ON semantic_evidence_links(subject_kind, subject_id);",
        "CREATE INDEX IF NOT EXISTS idx_semantic_evidence_atom ON semantic_evidence_links(atom_id);",
        "CREATE INDEX IF NOT EXISTS idx_semantic_evidence_role ON semantic_evidence_links(evidence_role);",
        "CREATE INDEX IF NOT EXISTS idx_materialization_audit_document ON materialization_audit(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_materialization_audit_code ON materialization_audit(code);",
    )
)
