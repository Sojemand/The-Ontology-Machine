"""Source-document and ontology schema contracts for corpus.db."""

from __future__ import annotations

from .types import IndexContract, TableContract

ONTOLOGY_TABLES = (
    TableContract(
        "source_documents",
        """CREATE TABLE IF NOT EXISTS source_documents (
    source_document_id TEXT PRIMARY KEY NOT NULL,
    source_uri TEXT NOT NULL,
    source_file_id TEXT,
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
    updated_at TEXT,
    FOREIGN KEY (first_document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (last_document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "source_documents aggregates page-level documents into deterministic source documents.",
    ),
    TableContract(
        "source_document_pages",
        """CREATE TABLE IF NOT EXISTS source_document_pages (
    source_document_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    page_index INTEGER NOT NULL CHECK (page_index >= 0),
    page_label TEXT,
    prev_document_id TEXT,
    next_document_id TEXT,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_document_id, document_id),
    FOREIGN KEY (source_document_id) REFERENCES source_documents(source_document_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (prev_document_id) REFERENCES documents(id),
    FOREIGN KEY (next_document_id) REFERENCES documents(id)
);""",
        "source_document_pages maps page-level documents into deterministic source-document order.",
    ),
    TableContract(
        "source_document_classifications",
        """CREATE TABLE IF NOT EXISTS source_document_classifications (
    source_document_id TEXT NOT NULL,
    classification_scope TEXT NOT NULL CHECK (classification_scope IN ('base', 'semantic_release', 'ontology')),
    ontology_id TEXT,
    document_type TEXT,
    category TEXT,
    subcategory TEXT,
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    status TEXT NOT NULL CHECK (status IN ('materialized', 'ambiguous', 'unresolved')),
    basis_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT NOT NULL DEFAULT 'basic_relation_mining',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    CHECK (
        (classification_scope = 'ontology' AND ontology_id IS NOT NULL)
        OR (classification_scope IN ('base', 'semantic_release') AND ontology_id IS NULL)
    ),
    FOREIGN KEY (source_document_id) REFERENCES source_documents(source_document_id) ON DELETE CASCADE,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
);""",
        "source_document_classifications stores source-level base, semantic-release and ontology-lens classifications.",
    ),
    TableContract(
        "ontology_lenses",
        """CREATE TABLE IF NOT EXISTS ontology_lenses (
    ontology_id TEXT PRIMARY KEY NOT NULL,
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
);""",
        "ontology_lenses stores user-selectable ontology views over the same corpus.",
    ),
    TableContract(
        "ontology_runs",
        """CREATE TABLE IF NOT EXISTS ontology_runs (
    run_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    run_kind TEXT NOT NULL CHECK (run_kind IN ('basic', 'extend', 'refine', 'merge', 'validate')),
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'waiting_user', 'complete', 'failed', 'rolled_back')),
    checkpoint_json TEXT NOT NULL DEFAULT '{}',
    stats_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
);""",
        "ontology_runs persists checkpointable ontology-agent run state.",
    ),
    TableContract(
        "ontology_terms",
        """CREATE TABLE IF NOT EXISTS ontology_terms (
    term_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    label TEXT NOT NULL,
    normalized_label TEXT NOT NULL,
    term_kind TEXT NOT NULL,
    definition TEXT,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'verified', 'rejected', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
);""",
        "ontology_terms stores lens-local terminology.",
    ),
    TableContract(
        "ontology_nodes",
        """CREATE TABLE IF NOT EXISTS ontology_nodes (
    node_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    canonical_label TEXT NOT NULL,
    source_ref_type TEXT,
    source_ref_id TEXT,
    summary TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'verified', 'rejected', 'deprecated')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
);""",
        "ontology_nodes stores lens-local graph nodes.",
    ),
    TableContract(
        "ontology_edges",
        """CREATE TABLE IF NOT EXISTS ontology_edges (
    edge_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    relation_label TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'verified', 'rejected', 'deprecated', 'hypothesis')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES ontology_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES ontology_nodes(node_id) ON DELETE CASCADE
);""",
        "ontology_edges stores lens-local graph edges.",
    ),
    TableContract(
        "ontology_assertions",
        """CREATE TABLE IF NOT EXISTS ontology_assertions (
    assertion_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    subject_ref_type TEXT NOT NULL,
    subject_ref_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_ref_type TEXT,
    object_ref_id TEXT,
    value_text TEXT,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'proposed', 'verified', 'rejected', 'deprecated', 'hypothesis')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
);""",
        "ontology_assertions stores lens-local subject-predicate-object facts.",
    ),
    TableContract(
        "ontology_evidence_links",
        """CREATE TABLE IF NOT EXISTS ontology_evidence_links (
    evidence_link_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    run_id TEXT,
    target_type TEXT NOT NULL CHECK (target_type IN ('term', 'node', 'edge', 'assertion', 'relation')),
    target_id TEXT NOT NULL,
    evidence_ref_type TEXT NOT NULL CHECK (evidence_ref_type IN ('document', 'source_document', 'structural_unit', 'evidence_atom', 'promotion', 'field', 'row')),
    evidence_ref_id TEXT NOT NULL,
    quote TEXT,
    rationale TEXT,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES ontology_runs(run_id) ON DELETE SET NULL
);""",
        "ontology_evidence_links grounds ontology items in corpus evidence.",
    ),
    TableContract(
        "ontology_activation",
        """CREATE TABLE IF NOT EXISTS ontology_activation (
    ontology_id TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'corpus' CHECK (scope = 'corpus'),
    scope_ref TEXT NOT NULL DEFAULT 'self' CHECK (scope_ref = 'self'),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    is_primary INTEGER NOT NULL DEFAULT 1 CHECK (is_primary IN (0, 1)),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority = 0),
    activated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ontology_id, scope, scope_ref),
    FOREIGN KEY (ontology_id) REFERENCES ontology_lenses(ontology_id) ON DELETE CASCADE
);""",
        "ontology_activation selects the single active primary corpus lens.",
    ),
    TableContract(
        "ontology_embedding_chunks",
        """CREATE TABLE IF NOT EXISTS ontology_embedding_chunks (
    chunk_id TEXT PRIMARY KEY NOT NULL,
    ontology_id TEXT NOT NULL,
    run_id TEXT,
    object_type TEXT NOT NULL CHECK (object_type IN ('term', 'node', 'edge', 'assertion', 'lens')),
    object_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
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
);""",
        "ontology_embedding_chunks stores chunk-level vectors for ontology objects.",
    ),
    TableContract(
        "ontology_edit_log",
        """CREATE TABLE IF NOT EXISTS ontology_edit_log (
    edit_id TEXT PRIMARY KEY NOT NULL,
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
);""",
        "ontology_edit_log records ontology edit units, verification, and before/after row snapshots.",
    ),
)

ONTOLOGY_INDEXES = (
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_ontology_activation_primary "
        "ON ontology_activation(scope, scope_ref) WHERE is_active = 1 AND is_primary = 1;"
    ),
    IndexContract("CREATE UNIQUE INDEX IF NOT EXISTS ux_source_document_pages_order ON source_document_pages(source_document_id, page_index);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_source_document_pages_document ON source_document_pages(document_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_source_document_pages_prev ON source_document_pages(prev_document_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_source_document_pages_next ON source_document_pages(next_document_id);"),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_source_doc_class_base_release "
        "ON source_document_classifications(source_document_id, classification_scope) "
        "WHERE ontology_id IS NULL;"
    ),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_source_doc_class_ontology "
        "ON source_document_classifications(source_document_id, classification_scope, ontology_id) "
        "WHERE ontology_id IS NOT NULL;"
    ),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_source_doc_class_scope_status ON source_document_classifications(classification_scope, status);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_source_doc_class_ontology ON source_document_classifications(ontology_id);"),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_rel_base_page_source_doc "
        "ON relations(document_id, relation_type, target_hint) "
        "WHERE relation_origin = 'base_graph' AND relation_type = 'page_of_source_document';"
    ),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_rel_base_page_target "
        "ON relations(document_id, relation_type, target_document_id) "
        "WHERE relation_origin = 'base_graph' AND relation_type IN ('next_page', 'previous_page');"
    ),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_lenses_status ON ontology_lenses(status);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_lenses_embedding_status ON ontology_lenses(embedding_status);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_runs_ontology_status ON ontology_runs(ontology_id, status);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_terms_ontology_label ON ontology_terms(ontology_id, normalized_label);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_nodes_ontology_type ON ontology_nodes(ontology_id, node_type);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_nodes_source_ref ON ontology_nodes(source_ref_type, source_ref_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_edges_ontology_type ON ontology_edges(ontology_id, relation_type);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_edges_source ON ontology_edges(source_node_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_edges_target ON ontology_edges(target_node_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_assertions_ontology_predicate ON ontology_assertions(ontology_id, predicate);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_assertions_subject ON ontology_assertions(subject_ref_type, subject_ref_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_evidence_target ON ontology_evidence_links(ontology_id, target_type, target_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_evidence_ref ON ontology_evidence_links(evidence_ref_type, evidence_ref_id);"),
    IndexContract(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_ontology_embedding_chunk_object_model "
        "ON ontology_embedding_chunks(ontology_id, object_type, object_id, chunk_index, model);"
    ),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_embedding_chunks_object ON ontology_embedding_chunks(ontology_id, object_type, object_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_edit_log_unit ON ontology_edit_log(edit_unit_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_ontology_edit_log_run ON ontology_edit_log(run_id);"),
)

__all__ = ["ONTOLOGY_INDEXES", "ONTOLOGY_TABLES"]
