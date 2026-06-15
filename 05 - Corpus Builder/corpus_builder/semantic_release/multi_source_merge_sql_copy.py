from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..database import connect, connect_readonly, ensure_schema
from .multi_source_merge_manifests import utc_iso
from .multi_source_merge_sql_base_graph import build_source_document_map, copy_base_graph
from .multi_source_merge_sql_documents import (
    copy_candidate_evidence,
    copy_document_keyed_tables,
    copy_document_promotions,
    copy_documents,
    copy_generated_id_table,
)
from .multi_source_merge_sql_entities import (
    copy_entity_attributes,
    copy_entity_relations,
    copy_fts_content,
    copy_relations,
    copy_semantic_evidence_links,
)
from .multi_source_merge_sql_helpers import count_active_documents, count_rows, table_exists
from .multi_source_merge_sql_map import mapping_by_source_document, source_document_map
from .multi_source_merge_sql_ontology import copy_ontology_layer
from .multi_source_merge_sql_refs import stringify_map


def merge_sql_databases(selection: Mapping[str, Any], mappings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    target_database_path = Path(str(selection.get("target_database_path") or "")).resolve(strict=False)
    target_database_path.parent.mkdir(parents=True, exist_ok=True)
    target_conn = connect(str(target_database_path))
    try:
        target_conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(target_conn)
        if count_active_documents(target_conn) != 0:
            raise ValueError("target_database_not_empty: filled merge requires an empty target database.")
        target_conn.execute("BEGIN IMMEDIATE")
        copied_documents = _copy_source_databases(selection, mappings, target_conn)
        _write_materialization_run(target_conn, selection, copied_documents)
        target_conn.commit()
        return {
            "written_database_path": str(target_database_path),
            "copied_document_count": copied_documents,
            "post_merge_counts": {
                "documents": count_active_documents(target_conn),
                "embeddings": count_rows(target_conn, "embeddings") + count_rows(target_conn, "embedding_chunks"),
                "source_documents": count_rows(target_conn, "source_documents"),
                "ontology_lenses": count_rows(target_conn, "ontology_lenses"),
            },
        }
    except Exception:
        if target_conn.in_transaction:
            target_conn.rollback()
        raise
    finally:
        target_conn.close()


def _copy_source_databases(
    selection: Mapping[str, Any],
    mappings: Sequence[Mapping[str, Any]],
    target_conn: sqlite3.Connection,
) -> int:
    copied_documents = 0
    target_artifact_root = Path(str(selection.get("target_artifact_root") or "")).resolve(strict=False)
    for source in selection.get("source_databases", []):
        if not isinstance(source, Mapping) or str(source.get("source_state") or "") == "empty":
            continue
        source_database_id = str(source.get("source_database_id") or "")
        copied_documents += _copy_source_database(
            target_conn=target_conn,
            target_artifact_root=target_artifact_root,
            merge_run_id=str(selection.get("merge_run_id") or ""),
            source=source,
            doc_map=source_document_map([dict(item) for item in mappings], source_database_id),
            doc_mappings=mapping_by_source_document([dict(item) for item in mappings], source_database_id),
        )
    return copied_documents


def _copy_source_database(
    *,
    target_conn: sqlite3.Connection,
    target_artifact_root: Path,
    merge_run_id: str,
    source: Mapping[str, Any],
    doc_map: Mapping[str, str],
    doc_mappings: Mapping[str, Mapping[str, Any]],
) -> int:
    source_path = Path(str(source.get("source_database_path") or "")).resolve(strict=False)
    if not source_path.exists():
        raise ValueError(f"source_database_missing: source database does not exist: {source_path}")
    source_conn = connect_readonly(str(source_path))
    try:
        if not table_exists(source_conn, "documents"):
            raise ValueError("source_database_invalid: source database does not contain documents.")
        source_rows = source_conn.execute("SELECT * FROM documents WHERE COALESCE(is_archived, 0) = 0 ORDER BY id").fetchall()
        source_document_ids = [str(row["id"]) for row in source_rows]
        if set(source_document_ids) != set(doc_map):
            raise ValueError("merge_id_map_invalid: merge ID map does not match source database rows.")
        _copy_source_document_rows(source_conn, target_conn, source_rows, target_artifact_root, merge_run_id, doc_map, doc_mappings)
        return len(source_rows)
    finally:
        source_conn.close()


def _copy_source_document_rows(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    source_rows: Sequence[sqlite3.Row],
    target_artifact_root: Path,
    merge_run_id: str,
    doc_map: Mapping[str, str],
    doc_mappings: Mapping[str, Mapping[str, Any]],
) -> None:
    source_document_ids = [str(row["id"]) for row in source_rows]
    first_mapping = next(iter(doc_mappings.values()), {})
    source_database_id = str(first_mapping.get("source_database_id") or "")
    source_doc_map = build_source_document_map(
        source_conn,
        source_rows,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
    )
    copy_documents(source_rows, target_conn, target_artifact_root, doc_map, doc_mappings, source_doc_map)
    generated_maps = copy_document_keyed_tables(source_conn, target_conn, source_document_ids, doc_map)
    atom_map = copy_generated_id_table(source_conn, target_conn, "evidence_atoms", "atom_id", source_document_ids, doc_map)
    candidate_map = copy_generated_id_table(source_conn, target_conn, "slot_candidates", "candidate_id", source_document_ids, doc_map)
    promotion_map = copy_document_promotions(source_conn, target_conn, source_document_ids, doc_map, candidate_map)
    copy_candidate_evidence(source_conn, target_conn, candidate_map, atom_map)
    entity_map = copy_generated_id_table(source_conn, target_conn, "document_entities", "entity_id", source_document_ids, doc_map)
    attribute_map = copy_entity_attributes(source_conn, target_conn, entity_map)
    relation_map = copy_entity_relations(source_conn, target_conn, entity_map, doc_map, source_document_ids)
    copy_semantic_evidence_links(source_conn, target_conn, atom_map, entity_map, attribute_map, relation_map)
    base_graph = copy_base_graph(
        source_conn,
        target_conn,
        source_doc_map,
        doc_map,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
    )
    document_relation_map = copy_relations(source_conn, target_conn, doc_map, base_graph.source_document_map, base_graph.structural_unit_map, source_document_ids)
    copy_ontology_layer(
        source_conn,
        target_conn,
        merge_run_id=merge_run_id,
        source_database_id=source_database_id,
        ref_maps={
            "document": stringify_map(doc_map),
            "page": stringify_map(doc_map),
            "source_document": stringify_map(base_graph.source_document_map),
            "structural_unit": stringify_map(base_graph.structural_unit_map),
            "evidence_atom": stringify_map(atom_map),
            "promotion": stringify_map(promotion_map),
            "field": stringify_map(generated_maps.get("field", {})),
            "row": stringify_map(generated_maps.get("row", {})),
            "entity": stringify_map(entity_map),
            "relation": stringify_map(document_relation_map),
        },
    )
    copy_fts_content(source_conn, target_conn, source_document_ids, doc_map)


def _write_materialization_run(
    target_conn: sqlite3.Connection,
    selection: Mapping[str, Any],
    copied_documents: int,
) -> None:
    target_conn.execute(
        "INSERT INTO materialization_runs (action, release_version, scope, processed_count, stale_count, error_count, notes, started_at, finished_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "multi_source_merge_databases",
            "",
            str(selection.get("merge_run_id") or ""),
            copied_documents,
            0,
            0,
            "filled_sql_and_artifacts",
            utc_iso(),
            utc_iso(),
        ),
    )
