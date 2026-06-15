from __future__ import annotations

from pathlib import Path
from typing import Any

from .ontology_validation_base_graph import validate_base_graph
from .ontology_validation_objects import validate_ontology_objects
from .ontology_validation_payloads import validate_ontology_payloads
from .ontology_validation_support import (
    REQUIRED_ONTOLOGY_TABLES,
    _check,
    _connect_readonly,
    _error,
    _finalize,
    _ontology_exists,
    _table_names,
)


def ontology_patch_validation(
    database_path: str | Path,
    *,
    ontology_id: str | None = None,
) -> dict[str, Any]:
    """Validate ontology/relation-layer consistency after an Ontology Agent edit."""

    resolved = Path(database_path).resolve(strict=False)
    report: dict[str, Any] = {
        "status": "pass",
        "database_path": str(resolved),
        "ontology_id": ontology_id,
        "checks": [],
        "warnings": [],
        "errors": [],
    }
    if not resolved.exists():
        _error(report, "database_missing", f"Corpus DB does not exist: {resolved}")
        return _finalize(report)
    if not resolved.is_file():
        _error(report, "database_not_file", f"Corpus DB must be a file: {resolved}")
        return _finalize(report)

    conn = _connect_readonly(resolved)
    try:
        tables = _table_names(conn)
        missing_tables = sorted(set(REQUIRED_ONTOLOGY_TABLES) - tables)
        _check(report, "required_tables", not missing_tables, {"missing_tables": missing_tables})
        if missing_tables:
            _error(report, "missing_required_tables", "Ontology validation requires the full ontology schema.")
            return _finalize(report)
        if ontology_id is not None and not _ontology_exists(conn, ontology_id):
            _error(report, "ontology_missing", f"Ontology lens does not exist: {ontology_id}")
            return _finalize(report)

        validate_base_graph(conn, report)
        validate_ontology_objects(conn, report, ontology_id=ontology_id)
        validate_ontology_payloads(conn, report, ontology_id=ontology_id)
    finally:
        conn.close()
    return _finalize(report)


__all__ = ["ontology_patch_validation"]
