"""Aggregated core corpus.db contract for document persistence and search."""

from __future__ import annotations

from .schema_documents import DOCUMENT_INDEXES, DOCUMENT_TABLES
from .schema_ontology import ONTOLOGY_INDEXES, ONTOLOGY_TABLES
from .schema_page_images import PAGE_IMAGE_INDEXES, PAGE_IMAGE_TABLES
from .schema_search import FTS_VIRTUAL_TABLE_SQL, SEARCH_INDEXES, SEARCH_TABLES
from .schema_structure import STRUCTURE_INDEXES, STRUCTURE_TABLES

CORE_TABLES = (*DOCUMENT_TABLES, *PAGE_IMAGE_TABLES, *SEARCH_TABLES, *ONTOLOGY_TABLES, *STRUCTURE_TABLES)
CORE_INDEXES = (*DOCUMENT_INDEXES, *PAGE_IMAGE_INDEXES, *SEARCH_INDEXES, *ONTOLOGY_INDEXES, *STRUCTURE_INDEXES)
