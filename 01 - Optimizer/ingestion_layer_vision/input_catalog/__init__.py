"""Typed input catalog surface with stable import path."""
from .surface import InputCatalog
from .types import CatalogEntry
from .validation import is_within as _is_within

__all__ = ["CatalogEntry", "InputCatalog", "_is_within"]
