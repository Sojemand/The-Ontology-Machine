"""Document persistence tables for the core corpus.db contract."""

from __future__ import annotations

from .types import CORPUS_SCHEMA_VERSION, TableContract

DOCUMENT_TABLES = (
    TableContract(
        "documents",
        """CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    source_file_path TEXT,
    source_page INTEGER,
    source_page_count INTEGER,
    source_document_id TEXT NOT NULL DEFAULT '',
    source_uri TEXT NOT NULL DEFAULT '',
    source_file_id TEXT,
    source_artifact_id TEXT NOT NULL DEFAULT '',
    ingest_run_id TEXT NOT NULL DEFAULT '',
    page_index INTEGER NOT NULL DEFAULT 0,
    page_label TEXT,
    materialization_order INTEGER NOT NULL DEFAULT 0,
    page_content_hash TEXT NOT NULL DEFAULT '',
    source_content_hash TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    file_size_bytes INTEGER,
    document_type TEXT NOT NULL,
    document_type_confidence REAL,
    category TEXT NOT NULL,
    subcategory TEXT,
    language TEXT DEFAULT 'und',
    is_scan BOOLEAN DEFAULT 0,
    has_handwriting BOOLEAN DEFAULT 0,
    page_count INTEGER DEFAULT 1,
    model TEXT NOT NULL,
    model_confidence REAL NOT NULL,
    needs_review BOOLEAN DEFAULT 0,
    interpreter_needs_review BOOLEAN DEFAULT 0,
    interpreter_review_reason TEXT,
    normalizer_needs_review BOOLEAN DEFAULT 0,
    normalizer_review_reason TEXT,
    vision_used BOOLEAN DEFAULT 0,
    materialization_version TEXT,
    projection_id TEXT,
    projection_fingerprint TEXT,
    validator_status TEXT NOT NULL,
    validator_issues_count INTEGER DEFAULT 0,
    content_structure TEXT,
    content_fields_json TEXT,
    content_rows_json TEXT,
    content_free_text TEXT,
    loaded_at TEXT NOT NULL,
    updated_at TEXT,
    is_archived BOOLEAN DEFAULT 0,
    archived_at TEXT,
    superseded_by TEXT,
    FOREIGN KEY (superseded_by) REFERENCES documents(id)
);""",
        "documents speichert technische Dokumentidentitaet, Klassifikation, Review- und Payload-Metadaten. Top-Level-Fakten liegen in document_promotions.",
    ),
    TableContract(
        "document_payloads",
        f"""CREATE TABLE IF NOT EXISTS document_payloads (
    document_id TEXT PRIMARY KEY,
    schema_version TEXT,
    corpus_schema_version TEXT NOT NULL DEFAULT '{CORPUS_SCHEMA_VERSION}',
    structured_json TEXT NOT NULL,
    raw_json TEXT,
    normalized_json TEXT,
    projection_json TEXT,
    original_file_name TEXT,
    original_media_type TEXT,
    original_blob BLOB,
    release_fingerprint TEXT,
    free_text TEXT,
    loaded_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "document_payloads speichert raw/structured/normalized plus Originaldatei als kalte Payload-Schichten ohne aktive Materialisierung.",
    ),
    TableContract(
        "extracted_fields",
        """CREATE TABLE IF NOT EXISTS extracted_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'text',
    numeric_value REAL,
    confidence TEXT,
    source TEXT,
    normalized_value TEXT,
    compact_value TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "extracted_fields enthaelt skalare content.fields und skalare Werte aus multi-value content.fields inklusive normalisierter Suchwerte.",
    ),
    TableContract(
        "extracted_rows",
        """CREATE TABLE IF NOT EXISTS extracted_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    row_json TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "extracted_rows enthaelt alle Tabellenzeilen als JSON inklusive _row_type und _row_index.",
    ),
    TableContract(
        "relations",
        """CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    target_hint TEXT NOT NULL,
    target_document_id TEXT,
    description TEXT,
    relation_origin TEXT NOT NULL DEFAULT 'observed',
    confidence REAL,
    evidence_refs TEXT,
    inference_policy_version TEXT,
    status TEXT NOT NULL DEFAULT 'observed',
    created_by TEXT NOT NULL DEFAULT 'corpus_builder',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (target_document_id) REFERENCES documents(id)
);""",
        "relations speichert dokumentbezogene Verknuepfungen und Zielhinweise.",
    ),
    TableContract(
        "tags",
        """CREATE TABLE IF NOT EXISTS tags (
    document_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    normalized_tag TEXT,
    compact_tag TEXT,
    PRIMARY KEY (document_id, tag),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "tags speichert zusaetzlich normalisierte und kompakte Suchwerte.",
    ),
    TableContract(
        "people",
        """CREATE TABLE IF NOT EXISTS people (
    document_id TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT,
    compact_name TEXT,
    PRIMARY KEY (document_id, name),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "people speichert zusaetzlich normalisierte und kompakte Suchwerte.",
    ),
    TableContract(
        "organizations",
        """CREATE TABLE IF NOT EXISTS organizations (
    document_id TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT,
    compact_name TEXT,
    PRIMARY KEY (document_id, name),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "organizations speichert zusaetzlich normalisierte und kompakte Suchwerte.",
    ),
)


__all__ = ["DOCUMENT_TABLES"]
