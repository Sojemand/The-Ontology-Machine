"""Search, embedding, and history contract for corpus.db."""

from __future__ import annotations

from .types import IndexContract, TableContract

SEARCH_TABLES = (
    TableContract(
        "embedding_chunks",
        """CREATE TABLE IF NOT EXISTS embedding_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_type TEXT NOT NULL,
    page INTEGER,
    source_kind TEXT NOT NULL,
    source_refs_json TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    vector BLOB NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "embedding_chunks speichert feinere Segment-, Zeilen- und Feldvektoren pro Dokument.",
    ),
    TableContract(
        "embeddings",
        """CREATE TABLE IF NOT EXISTS embeddings (
    document_id TEXT PRIMARY KEY,
    embedding_text TEXT NOT NULL,
    vector BLOB NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);""",
        "embeddings speichert kuratierten Suchtext und Vektoren im selben Corpus.",
    ),
    TableContract(
        "documents_fts_content",
        """CREATE TABLE IF NOT EXISTS documents_fts_content (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    content_free_text TEXT,
    fields_text TEXT,
    tags_text TEXT,
    people_text TEXT,
    orgs_text TEXT
);""",
        "documents_fts ist der Volltextindex ueber free_text, Feldwerte, Zeilentexte und leichte Metadaten.",
    ),
    TableContract(
        "load_history",
        """CREATE TABLE IF NOT EXISTS load_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    action TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT,
    timestamp TEXT NOT NULL,
    details TEXT
);""",
        "load_history dokumentiert Lade-, Skip- und Archivierungsverlaeufe.",
    ),
)

SEARCH_INDEXES = (
    IndexContract("CREATE INDEX IF NOT EXISTS idx_embedding_chunks_document ON embedding_chunks(document_id);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_embedding_chunks_page ON embedding_chunks(page);"),
    IndexContract("CREATE INDEX IF NOT EXISTS idx_embedding_chunks_type ON embedding_chunks(chunk_type);"),
)

FTS_VIRTUAL_TABLE_SQL = """CREATE VIRTUAL TABLE documents_fts USING fts5(
    content_free_text,
    fields_text,
    tags_text,
    people_text,
    orgs_text,
    content='documents_fts_content',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
)"""
