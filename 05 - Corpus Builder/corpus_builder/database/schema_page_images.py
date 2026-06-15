"""Separate page image table contract for optional image blobs in corpus.db."""

from __future__ import annotations

from .types import IndexContract, TableContract

PAGE_IMAGE_TABLES = (
    TableContract(
        "document_page_images",
        """CREATE TABLE IF NOT EXISTS document_page_images (
    document_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    image_sha256 TEXT,
    image_blob BLOB NOT NULL,
    PRIMARY KEY (document_id, page),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    CHECK (page > 0),
    CHECK (byte_size >= 0)
);""",
        "document_page_images speichert optionale Seitenbilder blob-separiert fuer Viewer-Zugriffe.",
    ),
)

PAGE_IMAGE_INDEXES = (
    IndexContract(
        "CREATE INDEX IF NOT EXISTS idx_page_images_document ON document_page_images(document_id);"
    ),
)

__all__ = ["PAGE_IMAGE_INDEXES", "PAGE_IMAGE_TABLES"]
