"""Stable corpus DB read-surface column contracts."""

from __future__ import annotations

from .schema_read_surface_base_columns import BASE_READ_SURFACE_COLUMNS
from .schema_read_surface_ontology_columns import ONTOLOGY_READ_SURFACE_COLUMNS
from .schema_read_surface_source_columns import SOURCE_READ_SURFACE_COLUMNS

READ_SURFACE_COLUMNS = {
    **BASE_READ_SURFACE_COLUMNS,
    **SOURCE_READ_SURFACE_COLUMNS,
    **ONTOLOGY_READ_SURFACE_COLUMNS,
}
