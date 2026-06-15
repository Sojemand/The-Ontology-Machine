"""DB repository for document_page_images writes and cleanup."""

from __future__ import annotations

import sqlite3


def replace_page_images(
    conn: sqlite3.Connection,
    document_id: str,
    page_images: list[dict[str, object]],
) -> None:
    conn.execute(
        "DELETE FROM document_page_images WHERE document_id = ?",
        (document_id,),
    )
    if not page_images:
        return
    conn.executemany(
        "INSERT INTO document_page_images "
        "(document_id, page, content_type, byte_size, image_sha256, image_blob) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                document_id,
                image["page"],
                image["content_type"],
                image["byte_size"],
                image["image_sha256"],
                image["image_blob"],
            )
            for image in page_images
        ],
    )


__all__ = ["replace_page_images"]
