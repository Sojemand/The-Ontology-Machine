"""Embedding vector persistence helpers."""

from __future__ import annotations

import sqlite3
import struct

from ..models.serialization import now_iso
from .types import EmbeddingBatchItem
from .validation import validate_vector_blob


def store_embedding(
    conn: sqlite3.Connection,
    doc_id: str,
    text: str,
    vector: list[float],
    model: str,
) -> None:
    vector_bytes = struct.pack(f"{len(vector)}f", *vector)
    conn.execute(
        "INSERT OR REPLACE INTO embeddings "
        "(document_id, embedding_text, vector, model, dimensions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, text, vector_bytes, model, len(vector), now_iso()),
    )


def store_embedding_chunk(
    conn: sqlite3.Connection,
    item: EmbeddingBatchItem,
    vector: list[float],
    model: str,
) -> None:
    if (
        item.target_kind != "chunk"
        or not item.chunk_id
        or item.chunk_index is None
        or not item.chunk_type
        or not item.source_kind
    ):
        raise ValueError("Chunk-Embedding braucht chunk_id, chunk_index, chunk_type und source_kind")

    vector_bytes = struct.pack(f"{len(vector)}f", *vector)
    conn.execute(
        "INSERT OR REPLACE INTO embedding_chunks "
        "(chunk_id, document_id, chunk_index, chunk_type, page, source_kind, "
        "source_refs_json, chunk_text, vector, model, dimensions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            item.chunk_id,
            item.document_id,
            item.chunk_index,
            item.chunk_type,
            item.page,
            item.source_kind,
            item.source_refs_json or "[]",
            item.text,
            vector_bytes,
            model,
            len(vector),
            now_iso(),
        ),
    )


def clear_embedding_chunks(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute("DELETE FROM embedding_chunks WHERE document_id = ?", (document_id,))


def load_embedding(
    vector_blob: bytes,
    *,
    expected_dimensions: int | None = None,
) -> list[float]:
    size = validate_vector_blob(vector_blob, expected_dimensions=expected_dimensions)
    try:
        return list(struct.unpack(f"{size}f", bytes(vector_blob)))
    except struct.error as exc:
        raise ValueError("Embedding-BLOB konnte nicht dekodiert werden") from exc


def checkpoint_wal(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
