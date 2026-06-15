export const ONTOLOGY_TEST_SCHEMA = `
  CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    document_type TEXT,
    category TEXT,
    subcategory TEXT,
    page_count INTEGER DEFAULT 1,
    content_free_text TEXT
  );
  CREATE TABLE document_promotions (
    promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    slot TEXT,
    slot_label TEXT,
    value_type TEXT,
    query_role TEXT,
    display_value TEXT,
    ordinal INTEGER,
    is_current INTEGER DEFAULT 1
  );
  CREATE TABLE source_documents (
    source_document_id TEXT PRIMARY KEY,
    source_uri TEXT NOT NULL,
    source_artifact_id TEXT NOT NULL,
    ingest_run_id TEXT NOT NULL,
    source_title TEXT,
    source_kind TEXT,
    page_count INTEGER NOT NULL CHECK (page_count >= 1),
    first_document_id TEXT NOT NULL,
    last_document_id TEXT NOT NULL,
    source_content_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
  );
  CREATE TABLE source_document_pages (
    source_document_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    page_index INTEGER NOT NULL CHECK (page_index >= 0),
    page_label TEXT,
    prev_document_id TEXT,
    next_document_id TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_document_id, document_id)
  );
  CREATE TABLE relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    relation_type TEXT,
    target_document_id TEXT,
    target_hint TEXT,
    relation_origin TEXT
  );
  CREATE TABLE ontology_lenses (
    ontology_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'ready', 'archived')),
    parent_ontology_id TEXT,
    intent_json TEXT NOT NULL DEFAULT '{}',
    policy_json TEXT NOT NULL DEFAULT '{}',
    embedding_status TEXT NOT NULL DEFAULT 'dirty' CHECK (embedding_status IN ('dirty', 'pending', 'clean', 'failed', 'unavailable')),
    embedding_error TEXT,
    embedding_updated_at TEXT,
    created_by TEXT NOT NULL DEFAULT 'ontology_agent',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (parent_ontology_id) REFERENCES ontology_lenses(ontology_id)
  );
  CREATE TABLE ontology_runs (
    run_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    run_kind TEXT NOT NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'waiting_user', 'complete', 'failed', 'rolled_back')),
    checkpoint_json TEXT NOT NULL DEFAULT '{}',
    stats_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
  );
  CREATE TABLE ontology_terms (
    term_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    label TEXT NOT NULL,
    normalized_label TEXT NOT NULL,
    term_kind TEXT NOT NULL,
    definition TEXT,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'verified', 'rejected', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
  );
  CREATE TABLE ontology_nodes (
    node_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    canonical_label TEXT NOT NULL,
    source_ref_type TEXT,
    source_ref_id TEXT,
    summary TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'verified', 'rejected', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
  );
  CREATE TABLE ontology_edges (
    edge_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    relation_label TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'verified', 'rejected', 'deprecated', 'hypothesis')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES ontology_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES ontology_nodes(node_id) ON DELETE CASCADE
  );
  CREATE TABLE ontology_assertions (
    assertion_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    subject_ref_type TEXT NOT NULL,
    subject_ref_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_ref_type TEXT,
    object_ref_id TEXT,
    value_text TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'verified', 'rejected', 'deprecated', 'hypothesis')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
  );
  CREATE TABLE ontology_evidence_links (
    evidence_link_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    run_id TEXT,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    evidence_ref_type TEXT NOT NULL,
    evidence_ref_id TEXT NOT NULL,
    quote TEXT,
    rationale TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES ontology_runs(run_id) ON DELETE SET NULL
  );
  CREATE TABLE ontology_activation (
    ontology_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'corpus',
    scope_ref TEXT NOT NULL DEFAULT 'self',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    is_primary INTEGER NOT NULL DEFAULT 1 CHECK (is_primary IN (0, 1)),
    priority INTEGER NOT NULL DEFAULT 0,
    activated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ontology_id, scope, scope_ref),
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
  );
  CREATE TABLE ontology_embedding_chunks (
    chunk_id TEXT PRIMARY KEY,
    ontology_id TEXT NOT NULL,
    run_id TEXT,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_type TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_refs_json TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    vector BLOB NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES ontology_runs(run_id) ON DELETE SET NULL
  );
  CREATE TABLE ontology_edit_log (
    edit_id TEXT PRIMARY KEY,
    edit_unit_id TEXT NOT NULL,
    run_id TEXT,
    ontology_id TEXT,
    tool_name TEXT NOT NULL,
    sql_summary TEXT NOT NULL,
    affected_tables_json TEXT NOT NULL DEFAULT '[]',
    affected_rows_json TEXT NOT NULL DEFAULT '{}',
    before_rows_json TEXT NOT NULL DEFAULT '{}',
    after_rows_json TEXT NOT NULL DEFAULT '{}',
    verification_status TEXT CHECK (verification_status IS NULL OR verification_status IN ('pass', 'warning', 'fail')),
    verification_report_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES ontology_runs(run_id) ON DELETE SET NULL,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE SET NULL
  );
`;
