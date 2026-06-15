"""Path-stable surface for report and structured-document serialization."""
from __future__ import annotations

from .report_io import (
    atomic_json_write,
    load_report,
    report_name,
    validation_report_from_dict,
)
from .structured_io import (
    load_structured_document,
    read_json_object,
    structured_document_from_dict,
)

__all__ = [
    "atomic_json_write",
    "load_report",
    "load_structured_document",
    "read_json_object",
    "report_name",
    "structured_document_from_dict",
    "validation_report_from_dict",
]
