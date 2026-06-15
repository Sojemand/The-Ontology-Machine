"""Read pending embedding source payloads from corpus.db."""

from __future__ import annotations

import sqlite3

from .types import EvidenceAtomSource, ExtractedFieldSource, ExtractedRowSource, PendingEmbeddingSource, PromotionSource


def fetch_pending_embedding_sources(conn: sqlite3.Connection) -> list[PendingEmbeddingSource]:
    rows = conn.execute(
        "SELECT d.id, d.file_name, d.file_path, d.document_type, "
        "d.page_count, p.normalized_json, p.free_text "
        "FROM documents d "
        "JOIN document_payloads p ON p.document_id = d.id "
        "LEFT JOIN embeddings e ON d.id = e.document_id "
        "LEFT JOIN ("
        "    SELECT document_id, COUNT(*) AS chunk_count "
        "    FROM embedding_chunks GROUP BY document_id"
        ") ec ON ec.document_id = d.id "
        "WHERE d.is_archived = 0 "
        "  AND (e.document_id IS NULL OR COALESCE(ec.chunk_count, 0) = 0) "
        "ORDER BY d.loaded_at ASC, d.id ASC"
    ).fetchall()
    return [
        PendingEmbeddingSource(
            document_id=str(row["id"]),
            normalized_json=str(row["normalized_json"] or ""),
            file_name=row["file_name"],
            file_path=row["file_path"],
            document_type=row["document_type"],
            page_count=int(row["page_count"]) if row["page_count"] is not None else None,
            payload_free_text=row["free_text"],
            evidence_atoms=_fetch_evidence_atoms(conn, str(row["id"])),
            promotions=_fetch_promotions(conn, str(row["id"])),
            rows=_fetch_rows(conn, str(row["id"])),
            fields=_fetch_fields(conn, str(row["id"])),
        )
        for row in rows
    ]


def _fetch_evidence_atoms(
    conn: sqlite3.Connection,
    document_id: str,
) -> tuple[EvidenceAtomSource, ...]:
    rows = conn.execute(
        "SELECT atom_id, atom_type, page, json_path, source_ref, text_value, context_label, context_window "
        "FROM evidence_atoms "
        "WHERE document_id = ? "
        "  AND atom_type IN ('segment', 'free_text') "
        "  AND COALESCE(text_value, '') != '' "
        "ORDER BY COALESCE(page, 0), atom_id",
        (document_id,),
    ).fetchall()
    return tuple(
        EvidenceAtomSource(
            atom_id=int(row["atom_id"]),
            atom_type=str(row["atom_type"]),
            page=int(row["page"]) if row["page"] is not None else None,
            json_path=str(row["json_path"]),
            source_ref=row["source_ref"],
            text_value=row["text_value"],
            context_label=row["context_label"],
            context_window=row["context_window"],
        )
        for row in rows
    )


def _fetch_rows(
    conn: sqlite3.Connection,
    document_id: str,
) -> tuple[ExtractedRowSource, ...]:
    rows = conn.execute(
        "SELECT id, row_index, row_json FROM extracted_rows "
        "WHERE document_id = ? ORDER BY row_index, id",
        (document_id,),
    ).fetchall()
    return tuple(
        ExtractedRowSource(
            row_id=int(row["id"]),
            row_index=int(row["row_index"]),
            row_json=str(row["row_json"]),
        )
        for row in rows
    )


def _fetch_fields(
    conn: sqlite3.Connection,
    document_id: str,
) -> tuple[ExtractedFieldSource, ...]:
    rows = conn.execute(
        "SELECT id, key, value, normalized_value FROM extracted_fields "
        "WHERE document_id = ? ORDER BY id",
        (document_id,),
    ).fetchall()
    return tuple(
        ExtractedFieldSource(
            field_id=int(row["id"]),
            key=str(row["key"]),
            value=str(row["value"]),
            normalized_value=row["normalized_value"],
        )
        for row in rows
    )


def _fetch_promotions(
    conn: sqlite3.Connection,
    document_id: str,
) -> tuple[PromotionSource, ...]:
    rows = conn.execute(
        "SELECT promotion_id, slot, slot_label, value_type, query_role, display_value, source_path "
        "FROM document_promotions WHERE document_id = ? AND is_current = 1 ORDER BY ordinal, promotion_id",
        (document_id,),
    ).fetchall()
    return tuple(
        PromotionSource(
            promotion_id=int(row["promotion_id"]),
            slot=str(row["slot"]),
            slot_label=row["slot_label"],
            value_type=row["value_type"],
            query_role=row["query_role"],
            display_value=str(row["display_value"]),
            source_path=row["source_path"],
        )
        for row in rows
    )
