from __future__ import annotations

import sqlite3
from typing import Mapping

from .multi_source_merge_sql_helpers import table_exists
from .multi_source_merge_sql_refs import merged_id, stringify_map


def build_table_id_map(
    rows: list[sqlite3.Row],
    column: str,
    prefix: str,
    merge_run_id: str,
    source_database_id: str,
) -> dict[str, str]:
    return {
        str(row[column]): merged_id(prefix, merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row[column])
        for row in rows
    }


def fetch_all(conn: sqlite3.Connection, table: str, order_column: str) -> list[sqlite3.Row]:
    if not table_exists(conn, table):
        return []
    return conn.execute(f"SELECT * FROM {table} ORDER BY {order_column}").fetchall()


def merged_ontology_ref_maps(
    ref_maps: Mapping[str, Mapping[str, str]],
    *,
    ontology_map: Mapping[str, str],
    term_map: Mapping[str, str],
    node_map: Mapping[str, str],
    edge_map: Mapping[str, str],
    assertion_map: Mapping[str, str],
) -> dict[str, dict[str, str]]:
    return {
        **{key: dict(value) for key, value in ref_maps.items()},
        "lens": dict(ontology_map),
        "term": dict(term_map),
        "node": dict(node_map),
        "edge": dict(edge_map),
        "assertion": dict(assertion_map),
    }


def replacement_map(ref_maps: Mapping[str, Mapping[str, str]], run_map: Mapping[str, str]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for mapping in ref_maps.values():
        replacements.update(stringify_map(mapping))
    replacements.update(stringify_map(run_map))
    return replacements


def empty_ontology_counts() -> dict[str, int]:
    return {
        "ontology_lenses": 0,
        "ontology_runs": 0,
        "ontology_terms": 0,
        "ontology_nodes": 0,
        "ontology_edges": 0,
        "ontology_assertions": 0,
        "ontology_source_document_classifications": 0,
        "ontology_activation": 0,
        "ontology_evidence_links": 0,
        "ontology_embedding_chunks": 0,
        "ontology_edit_log": 0,
    }

