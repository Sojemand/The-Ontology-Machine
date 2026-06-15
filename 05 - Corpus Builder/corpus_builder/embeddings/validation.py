"""Validation stage for embedding contracts."""

from __future__ import annotations

from typing import Sequence


def validate_vectors(
    vectors: Sequence[Sequence[float]],
    *,
    expected_count: int,
    expected_dimensions: int,
) -> None:
    if len(vectors) != expected_count:
        raise ValueError(
            f"Provider lieferte {len(vectors)} Embeddings fuer {expected_count} Texte"
        )

    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) > 1:
        raise ValueError(f"Uneinheitliche Embedding-Dimensionen: {sorted(dimensions)}")

    actual_dimensions = next(iter(dimensions), 0)
    if expected_dimensions > 0 and actual_dimensions != expected_dimensions:
        raise ValueError(
            f"Unerwartete Embedding-Dimension {actual_dimensions} "
            f"(erwartet {expected_dimensions})"
        )


def validate_vector_blob(
    vector_blob: bytes,
    *,
    expected_dimensions: int | None = None,
) -> int:
    raw = bytes(vector_blob)
    if not raw:
        raise ValueError("Leeres Embedding-BLOB")
    if len(raw) % 4 != 0:
        raise ValueError(f"Ungueltige Embedding-BLOB-Laenge: {len(raw)} Bytes")

    size = len(raw) // 4
    if expected_dimensions is not None and size != expected_dimensions:
        raise ValueError(
            f"Embedding-BLOB hat {size} Dimensionen, erwartet wurden "
            f"{expected_dimensions}"
        )
    return size
