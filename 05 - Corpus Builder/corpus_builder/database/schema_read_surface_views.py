"""Stable corpus DB read-surface view definitions."""

from __future__ import annotations

from .schema_read_surface_base_views import BASE_READ_SURFACE_VIEWS
from .schema_read_surface_ontology_views import ONTOLOGY_READ_SURFACE_VIEWS
from .schema_read_surface_source_views import SOURCE_READ_SURFACE_VIEWS

READ_SURFACE_VIEWS = (
    *BASE_READ_SURFACE_VIEWS,
    *SOURCE_READ_SURFACE_VIEWS,
    *ONTOLOGY_READ_SURFACE_VIEWS,
)
