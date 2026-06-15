"""Deterministic base graph mining for materialized corpus databases."""

from __future__ import annotations

import sqlite3
from typing import Any

from .basic_relation_classification import insert_source_document_classifications
from .basic_relation_structural import insert_structural_units
from .basic_relation_support import fetch_documents, group_documents
from .basic_relation_validation import validate_base_graph
from .basic_relation_writes import (
    clear_base_graph,
    insert_relations,
    insert_source_document,
    insert_source_document_pages,
)


def basic_relation_mining(conn: sqlite3.Connection, *, dry_run: bool = False) -> dict[str, Any]:
    """Build the deterministic source-document base graph without LLM calls."""
    documents, unresolved_documents = fetch_documents(conn)
    grouped, rejected_groups = group_documents(documents)
    report: dict[str, Any] = {
        "status": "pass",
        "source_documents": len(grouped),
        "source_document_pages": sum(len(group) for group in grouped.values()),
        "relations_inserted": 0,
        "structural_units_inserted": 0,
        "structural_unit_relations_inserted": 0,
        "source_document_classifications_inserted": 0,
        "unresolved_documents": unresolved_documents,
        "rejected_groups": rejected_groups,
        "warnings": [],
        "errors": [],
        "dry_run": dry_run,
    }
    if dry_run:
        if unresolved_documents or rejected_groups:
            report["status"] = "warning"
        return report

    try:
        clear_base_graph(conn, grouped.keys())
        counters = _insert_base_graph(conn, grouped.values())
        report.update(counters)
        report["warnings"].extend(validate_base_graph(conn))
        if unresolved_documents or rejected_groups or report["warnings"]:
            report["status"] = "warning"
        conn.commit()
    except Exception as exc:
        conn.rollback()
        report["status"] = "fail"
        report["errors"].append(str(exc))
    return report


def _insert_base_graph(conn: sqlite3.Connection, groups: Any) -> dict[str, int]:
    relations_inserted = 0
    structural_units_inserted = 0
    structural_unit_relations_inserted = 0
    classifications_inserted = 0
    for group in groups:
        insert_source_document(conn, group)
        insert_source_document_pages(conn, group)
        classifications_inserted += insert_source_document_classifications(conn, group)
        relations_inserted += insert_relations(conn, group)
        units_count, unit_relations_count = insert_structural_units(conn, group)
        structural_units_inserted += units_count
        structural_unit_relations_inserted += unit_relations_count
    return {
        "relations_inserted": relations_inserted,
        "structural_units_inserted": structural_units_inserted,
        "structural_unit_relations_inserted": structural_unit_relations_inserted,
        "source_document_classifications_inserted": classifications_inserted,
    }


__all__ = ["basic_relation_mining"]
