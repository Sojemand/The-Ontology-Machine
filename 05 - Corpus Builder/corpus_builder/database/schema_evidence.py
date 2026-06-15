"""Evidence and candidate contract for semantic corpus.db stages."""

from __future__ import annotations

from .types import IndexContract, TableContract

EVIDENCE_TABLES = (
    TableContract(
        "evidence_atoms",
        """CREATE TABLE IF NOT EXISTS evidence_atoms (
    atom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    atom_type TEXT NOT NULL,
    json_path TEXT NOT NULL,
    anchor_kind TEXT,
    anchor_key TEXT,
    page INTEGER,
    row_index INTEGER,
    column_key TEXT,
    source_ref TEXT,
    text_value TEXT,
    normalized_text TEXT,
    compact_text TEXT,
    numeric_value REAL,
    date_value TEXT,
    currency TEXT,
    context_label TEXT,
    context_window TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "evidence_atoms enthaelt atomare Evidenz mit JSON-Pfad, Provenienz und Normformen.",
    ),
    TableContract(
        "slot_candidates",
        """CREATE TABLE IF NOT EXISTS slot_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    display_value TEXT NOT NULL,
    normalized_value TEXT,
    compact_value TEXT,
    numeric_value REAL,
    date_value TEXT,
    strategy TEXT NOT NULL,
    confidence REAL,
    ambiguity_group TEXT,
    is_projection_backed BOOLEAN DEFAULT 0,
    candidate_layer TEXT NOT NULL DEFAULT 'base',
    candidate_origin TEXT,
    source_refs_json TEXT,
    origin_path TEXT,
    origin_kind TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "slot_candidates speichert mehrdeutige semantische Kandidaten statt nur eines vermeintlich wahren Feldwerts.",
    ),
    TableContract(
        "document_promotions",
        """CREATE TABLE IF NOT EXISTS document_promotions (
    promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    slot_label TEXT,
    value_type TEXT NOT NULL,
    query_role TEXT,
    display_value TEXT NOT NULL,
    normalized_value TEXT,
    compact_value TEXT,
    numeric_value REAL,
    date_value TEXT,
    value_json TEXT,
    ordinal INTEGER NOT NULL DEFAULT 0,
    confidence REAL,
    candidate_id INTEGER,
    source_path TEXT,
    source_refs_json TEXT,
    projection_id TEXT,
    release_fingerprint TEXT,
    materialization_version TEXT,
    is_current BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES slot_candidates(candidate_id) ON DELETE SET NULL
);""",
        "document_promotions speichert die ausgewaehlten dynamischen Top-Level Promotion-Werte pro Dokument.",
    ),
    TableContract(
        "candidate_evidence",
        """CREATE TABLE IF NOT EXISTS candidate_evidence (
    candidate_id INTEGER NOT NULL,
    atom_id INTEGER NOT NULL,
    PRIMARY KEY (candidate_id, atom_id),
    FOREIGN KEY (candidate_id) REFERENCES slot_candidates(candidate_id) ON DELETE CASCADE,
    FOREIGN KEY (atom_id) REFERENCES evidence_atoms(atom_id) ON DELETE CASCADE
);""",
        "candidate_evidence verknuepft Kandidaten mit konkreten Evidence-Atoms.",
    ),
)

EVIDENCE_INDEXES = tuple(
    IndexContract(sql)
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_atoms_document ON evidence_atoms(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_type ON evidence_atoms(atom_type);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_path ON evidence_atoms(json_path);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_anchor ON evidence_atoms(anchor_kind, anchor_key);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_source_ref ON evidence_atoms(source_ref);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_normalized ON evidence_atoms(normalized_text);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_compact ON evidence_atoms(compact_text);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_numeric ON evidence_atoms(numeric_value);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_date ON evidence_atoms(date_value);",
        "CREATE INDEX IF NOT EXISTS idx_atoms_page ON evidence_atoms(page);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_document ON slot_candidates(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_slot ON slot_candidates(slot);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_slot_value ON slot_candidates(slot, normalized_value);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_compact ON slot_candidates(compact_value);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_numeric ON slot_candidates(numeric_value);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_date ON slot_candidates(date_value);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_projection ON slot_candidates(is_projection_backed);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_layer ON slot_candidates(candidate_layer);",
        "CREATE INDEX IF NOT EXISTS idx_candidates_origin ON slot_candidates(candidate_origin);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_document ON document_promotions(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_slot ON document_promotions(slot);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_slot_value ON document_promotions(slot, normalized_value);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_compact ON document_promotions(compact_value);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_numeric ON document_promotions(slot, numeric_value);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_date ON document_promotions(slot, date_value);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_current ON document_promotions(is_current, slot);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_role ON document_promotions(query_role);",
        "CREATE INDEX IF NOT EXISTS idx_document_promotions_release ON document_promotions(release_fingerprint);",
        "CREATE INDEX IF NOT EXISTS idx_candidate_evidence_atom ON candidate_evidence(atom_id);",
    )
)
