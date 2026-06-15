from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Mapping

from .multi_source_merge_sql_base_graph import copy_ontology_source_document_classifications
from .multi_source_merge_sql_helpers import table_exists
from .multi_source_merge_sql_ontology_links import copy_edit_log, copy_embedding_chunks, copy_evidence_links
from .multi_source_merge_sql_ontology_rows import (
    copy_activation,
    copy_assertions,
    copy_edges,
    copy_lenses,
    copy_nodes,
    copy_runs,
    copy_terms,
)
from .multi_source_merge_sql_ontology_support import (
    build_table_id_map,
    empty_ontology_counts,
    fetch_all,
    merged_ontology_ref_maps,
    replacement_map,
)


@dataclass(frozen=True)
class OntologyCopyResult:
    ontology_map: dict[str, str]
    counts: dict[str, int]


def copy_ontology_layer(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    *,
    merge_run_id: str,
    source_database_id: str,
    ref_maps: Mapping[str, Mapping[str, str]],
) -> OntologyCopyResult:
    if not table_exists(source_conn, "ontology_lenses") or not table_exists(target_conn, "ontology_lenses"):
        return OntologyCopyResult({}, empty_ontology_counts())
    lens_rows = fetch_all(source_conn, "ontology_lenses", "ontology_id")
    ontology_map = build_table_id_map(lens_rows, "ontology_id", "mrg_ont", merge_run_id, source_database_id)
    run_map = build_table_id_map(fetch_all(source_conn, "ontology_runs", "run_id"), "run_id", "mrg_orun", merge_run_id, source_database_id)
    term_map = build_table_id_map(fetch_all(source_conn, "ontology_terms", "term_id"), "term_id", "mrg_term", merge_run_id, source_database_id)
    node_map = build_table_id_map(fetch_all(source_conn, "ontology_nodes", "node_id"), "node_id", "mrg_node", merge_run_id, source_database_id)
    edge_map = build_table_id_map(fetch_all(source_conn, "ontology_edges", "edge_id"), "edge_id", "mrg_edge", merge_run_id, source_database_id)
    assertion_map = build_table_id_map(
        fetch_all(source_conn, "ontology_assertions", "assertion_id"),
        "assertion_id",
        "mrg_ass",
        merge_run_id,
        source_database_id,
    )
    merged_ref_maps = merged_ontology_ref_maps(
        ref_maps,
        ontology_map=ontology_map,
        term_map=term_map,
        node_map=node_map,
        edge_map=edge_map,
        assertion_map=assertion_map,
    )
    replacements = replacement_map(merged_ref_maps, run_map)
    counts = empty_ontology_counts()
    counts["ontology_lenses"] = copy_lenses(target_conn, lens_rows, ontology_map, replacements)
    counts["ontology_runs"] = copy_runs(source_conn, target_conn, ontology_map, run_map, replacements)
    counts["ontology_terms"] = copy_terms(source_conn, target_conn, ontology_map, term_map, replacements)
    counts["ontology_nodes"] = copy_nodes(source_conn, target_conn, ontology_map, node_map, merged_ref_maps, replacements)
    counts["ontology_edges"] = copy_edges(source_conn, target_conn, ontology_map, node_map, edge_map, replacements)
    counts["ontology_assertions"] = copy_assertions(source_conn, target_conn, ontology_map, assertion_map, merged_ref_maps, replacements)
    counts["ontology_source_document_classifications"] = copy_ontology_source_document_classifications(
        source_conn,
        target_conn,
        ref_maps.get("source_document", {}),
        ontology_map,
    )
    counts["ontology_activation"] = copy_activation(source_conn, target_conn, ontology_map)
    counts["ontology_evidence_links"] = copy_evidence_links(
        source_conn,
        target_conn,
        ontology_map,
        run_map,
        merged_ref_maps,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
    )
    counts["ontology_embedding_chunks"] = copy_embedding_chunks(
        source_conn,
        target_conn,
        ontology_map,
        run_map,
        merged_ref_maps,
        replacements,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
    )
    counts["ontology_edit_log"] = copy_edit_log(
        source_conn,
        target_conn,
        ontology_map,
        run_map,
        replacements,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
    )
    return OntologyCopyResult(ontology_map, counts)

