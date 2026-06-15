from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .multi_source_merge_sql_helpers import insert_row
from .multi_source_merge_sql_refs import merged_id, merged_ref_id, rewrite_json_text
from .multi_source_merge_sql_ontology_support import fetch_all


def copy_lenses(target_conn, rows, ontology_map, replacements) -> int:
    pending = {str(row["ontology_id"]): row for row in rows}
    copied = 0
    while pending:
        progressed = False
        for ontology_id, row in list(pending.items()):
            parent_id = str(row["parent_ontology_id"] or "")
            if parent_id and parent_id in pending:
                continue
            insert_row(
                target_conn,
                "ontology_lenses",
                row,
                overrides={
                    "ontology_id": ontology_map[ontology_id],
                    "parent_ontology_id": ontology_map.get(parent_id) if parent_id else None,
                    "intent_json": rewrite_json_text(row["intent_json"], replacements),
                    "policy_json": rewrite_json_text(row["policy_json"], replacements),
                },
            )
            pending.pop(ontology_id)
            copied += 1
            progressed = True
        if not progressed:
            cycle_items = list(pending.items())
            ontology_id, row = next(
                ((item_id, item_row) for item_id, item_row in cycle_items if str(item_row["parent_ontology_id"] or "") == item_id),
                cycle_items[0],
            )
            insert_row(
                target_conn,
                "ontology_lenses",
                row,
                overrides={
                    "ontology_id": ontology_map[ontology_id],
                    "parent_ontology_id": None,
                    "intent_json": rewrite_json_text(row["intent_json"], replacements),
                    "policy_json": rewrite_json_text(row["policy_json"], replacements),
                },
            )
            pending.pop(ontology_id)
            copied += 1
    return copied


def copy_runs(source_conn, target_conn, ontology_map, run_map, replacements) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_runs", "run_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        if not ontology_id:
            continue
        insert_row(
            target_conn,
            "ontology_runs",
            row,
            overrides={
                "run_id": run_map[str(row["run_id"])],
                "ontology_id": ontology_id,
                "checkpoint_json": rewrite_json_text(row["checkpoint_json"], replacements),
                "stats_json": rewrite_json_text(row["stats_json"], replacements),
            },
        )
        count += 1
    return count


def copy_terms(source_conn, target_conn, ontology_map, term_map, replacements) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_terms", "term_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        if not ontology_id:
            continue
        insert_row(
            target_conn,
            "ontology_terms",
            row,
            overrides={
                "term_id": term_map[str(row["term_id"])],
                "ontology_id": ontology_id,
                "aliases_json": rewrite_json_text(row["aliases_json"], replacements),
            },
        )
        count += 1
    return count


def copy_nodes(source_conn, target_conn, ontology_map, node_map, ref_maps, replacements) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_nodes", "node_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        if not ontology_id:
            continue
        source_ref_type, source_ref_id = optional_ref(row["source_ref_type"], row["source_ref_id"], ref_maps)
        insert_row(
            target_conn,
            "ontology_nodes",
            row,
            overrides={
                "node_id": node_map[str(row["node_id"])],
                "ontology_id": ontology_id,
                "source_ref_type": source_ref_type,
                "source_ref_id": source_ref_id,
                "attributes_json": rewrite_json_text(row["attributes_json"], replacements),
            },
        )
        count += 1
    return count


def copy_edges(source_conn, target_conn, ontology_map, node_map, edge_map, replacements) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_edges", "edge_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        source_node_id = node_map.get(str(row["source_node_id"]))
        target_node_id = node_map.get(str(row["target_node_id"]))
        if not ontology_id or not source_node_id or not target_node_id:
            continue
        insert_row(
            target_conn,
            "ontology_edges",
            row,
            overrides={
                "edge_id": edge_map[str(row["edge_id"])],
                "ontology_id": ontology_id,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "attributes_json": rewrite_json_text(row["attributes_json"], replacements),
            },
        )
        count += 1
    return count


def copy_assertions(source_conn, target_conn, ontology_map, assertion_map, ref_maps, replacements) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_assertions", "assertion_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        subject_id = merged_ref_id(row["subject_ref_type"], row["subject_ref_id"], ref_maps)
        object_id = merged_ref_id(row["object_ref_type"], row["object_ref_id"], ref_maps) if row["object_ref_type"] or row["object_ref_id"] else None
        if not ontology_id or not subject_id or ((row["object_ref_type"] or row["object_ref_id"]) and not object_id):
            continue
        insert_row(
            target_conn,
            "ontology_assertions",
            row,
            overrides={
                "assertion_id": assertion_map[str(row["assertion_id"])],
                "ontology_id": ontology_id,
                "subject_ref_id": subject_id,
                "object_ref_id": object_id,
            },
        )
        count += 1
    return count


def copy_activation(source_conn, target_conn, ontology_map) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_activation", "ontology_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        if not ontology_id:
            continue
        is_primary = int(row["is_primary"] or 0)
        if int(row["is_active"] or 0) and is_primary and target_has_primary_activation(target_conn):
            is_primary = 0
        insert_row(target_conn, "ontology_activation", row, overrides={"ontology_id": ontology_id, "is_primary": is_primary})
        count += 1
    return count


def optional_ref(ref_type: Any, ref_id: Any, ref_maps: Mapping[str, Mapping[str, str]]) -> tuple[Any, Any]:
    if not ref_type or not ref_id:
        return ref_type, ref_id
    mapping = ref_maps.get(str(ref_type))
    if mapping is None:
        return ref_type, ref_id
    mapped = mapping.get(str(ref_id))
    return (ref_type, mapped) if mapped else (None, None)


def target_has_primary_activation(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM ontology_activation WHERE is_active = 1 AND is_primary = 1 LIMIT 1",
    ).fetchone()
    return row is not None
