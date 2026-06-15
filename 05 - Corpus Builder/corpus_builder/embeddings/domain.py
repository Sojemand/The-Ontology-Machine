"""Path-stable domain surface for embedding text, chunks, and vector math."""

from __future__ import annotations

from .chunk_domain import build_embedding_chunks
from .math_domain import cosine_similarity, parse_document_json
from .text_domain import build_embedding_text, build_inline_source

__all__ = [
    "build_embedding_chunks",
    "build_embedding_text",
    "build_inline_source",
    "cosine_similarity",
    "parse_document_json",
]
