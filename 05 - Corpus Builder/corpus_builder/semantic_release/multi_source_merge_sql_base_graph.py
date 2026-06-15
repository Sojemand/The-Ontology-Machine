from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Mapping, Sequence

from .multi_source_merge_sql_base_graph_rows import (
    copy_source_document_classifications,
    copy_source_document_pages,
    copy_source_documents,
    copy_structural_unit_relations,
    copy_structural_units,
    fetch_rows_by_source_documents,
)
from .multi_source_merge_sql_helpers import table_exists
from .multi_source_merge_sql_refs import merged_id, stringify_map
from .sql_parameter_batches import iter_parameter_batches


@dataclass(frozen=True)
class BaseGraphCopyResult:
    source_document_map: dict[str, str]
    structural_unit_map: dict[str, str]
    counts: dict[str, int]


def build_source_document_map(
    source_conn: sqlite3.Connection,
    source_rows: Sequence[sqlite3.Row],
    *,
    merge_run_id: str,
    source_database_id: str,
) -> dict[str, str]:
    source_ids: set[str] = {
        str(row["source_document_id"] or "")
        for row in source_rows
        if "source_document_id" in row.keys() and str(row["source_document_id"] or "")
    }
    document_ids = [str(row["id"]) for row in source_rows]
    if table_exists(source_conn, "source_document_pages"):
        for batch in iter_parameter_batches(document_ids):
            placeholders = ", ".join("?" for _ in batch)
            rows = source_conn.execute(
                f"SELECT DISTINCT source_document_id FROM source_document_pages WHERE document_id IN ({placeholders})",
                batch,
            ).fetchall()
            source_ids.update(str(row["source_document_id"] or "") for row in rows if str(row["source_document_id"] or ""))
    return {
        source_id: merged_id("mrg_sd", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=source_id)
        for source_id in sorted(source_ids)
    }


def copy_base_graph(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_document_map: Mapping[str, str],
    doc_map: Mapping[str, str],
    *,
    merge_run_id: str,
    source_database_id: str,
) -> BaseGraphCopyResult:
    counts = _empty_counts()
    source_ids = sorted(source_document_map)
    if not source_ids:
        return BaseGraphCopyResult(dict(source_document_map), {}, counts)
    replacements = {**stringify_map(doc_map), **stringify_map(source_document_map)}
    counts["source_documents"] = copy_source_documents(source_conn, target_conn, source_ids, source_document_map, doc_map, replacements)
    if counts["source_documents"] == 0:
        return BaseGraphCopyResult(dict(source_document_map), {}, counts)
    counts["source_document_pages"] = copy_source_document_pages(source_conn, target_conn, source_ids, source_document_map, doc_map, replacements)
    counts["source_document_classifications"] = copy_source_document_classifications(
        source_conn,
        target_conn,
        source_ids,
        source_document_map,
        ontology_map=None,
    )
    unit_rows = fetch_rows_by_source_documents(source_conn, "structural_units", source_ids, "source_document_id")
    unit_map = {
        str(row["unit_id"]): merged_id("mrg_su", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row["unit_id"])
        for row in unit_rows
    }
    unit_replacements = {**replacements, **stringify_map(unit_map)}
    counts["structural_units"] = copy_structural_units(target_conn, unit_rows, source_document_map, doc_map, unit_map, unit_replacements)
    counts["structural_unit_relations"] = copy_structural_unit_relations(
        source_conn,
        target_conn,
        source_ids,
        source_document_map,
        unit_map,
        unit_replacements,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
    )
    return BaseGraphCopyResult(dict(source_document_map), unit_map, counts)


def copy_ontology_source_document_classifications(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_document_map: Mapping[str, str],
    ontology_map: Mapping[str, str],
) -> int:
    return copy_source_document_classifications(
        source_conn,
        target_conn,
        sorted(source_document_map),
        source_document_map,
        ontology_map=ontology_map,
    )


def _empty_counts() -> dict[str, int]:
    return {
        "source_documents": 0,
        "source_document_pages": 0,
        "source_document_classifications": 0,
        "structural_units": 0,
        "structural_unit_relations": 0,
    }

