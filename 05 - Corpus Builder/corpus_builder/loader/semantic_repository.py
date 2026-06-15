"""Semantic materialization persistence facade for the loader repository."""

from __future__ import annotations

from .semantic_repository_core import (
    clear_semantic_materialization,
    insert_document_promotion,
    insert_materialization_audits,
    insert_processing_state,
)
from .semantic_repository_entities import insert_document_entities
from .semantic_repository_evidence import (
    SUBJECT_DOCUMENT_ENTITY,
    SUBJECT_ENTITY_ATTRIBUTE,
    SUBJECT_ENTITY_RELATION,
    build_semantic_evidence_index,
)

__all__ = [
    "SUBJECT_DOCUMENT_ENTITY",
    "SUBJECT_ENTITY_ATTRIBUTE",
    "SUBJECT_ENTITY_RELATION",
    "build_semantic_evidence_index",
    "clear_semantic_materialization",
    "insert_document_entities",
    "insert_document_promotion",
    "insert_materialization_audits",
    "insert_processing_state",
]
