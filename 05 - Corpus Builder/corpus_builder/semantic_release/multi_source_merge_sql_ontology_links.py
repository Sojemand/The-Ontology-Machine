from __future__ import annotations

from .multi_source_merge_sql_helpers import insert_row
from .multi_source_merge_sql_refs import merged_id, merged_ref_id, rewrite_json_text
from .multi_source_merge_sql_ontology_support import fetch_all


def copy_evidence_links(source_conn, target_conn, ontology_map, run_map, ref_maps, *, merge_run_id, source_database_id) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_evidence_links", "evidence_link_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        target_id = merged_ref_id(row["target_type"], row["target_id"], ref_maps)
        evidence_ref_id = merged_ref_id(row["evidence_ref_type"], row["evidence_ref_id"], ref_maps)
        run_id = run_map.get(str(row["run_id"])) if row["run_id"] is not None else None
        if not ontology_id or not target_id or not evidence_ref_id:
            continue
        insert_row(
            target_conn,
            "ontology_evidence_links",
            row,
            overrides={
                "evidence_link_id": merged_id("mrg_ev", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row["evidence_link_id"]),
                "ontology_id": ontology_id,
                "run_id": run_id,
                "target_id": target_id,
                "evidence_ref_id": evidence_ref_id,
            },
        )
        count += 1
    return count


def copy_embedding_chunks(source_conn, target_conn, ontology_map, run_map, ref_maps, replacements, *, merge_run_id, source_database_id) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_embedding_chunks", "chunk_id"):
        ontology_id = ontology_map.get(str(row["ontology_id"]))
        object_id = merged_ref_id(row["object_type"], row["object_id"], ref_maps)
        run_id = run_map.get(str(row["run_id"])) if row["run_id"] is not None else None
        if not ontology_id or not object_id:
            continue
        insert_row(
            target_conn,
            "ontology_embedding_chunks",
            row,
            overrides={
                "chunk_id": merged_id("mrg_och", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row["chunk_id"]),
                "ontology_id": ontology_id,
                "run_id": run_id,
                "object_id": object_id,
                "source_refs_json": rewrite_json_text(row["source_refs_json"], replacements),
            },
        )
        count += 1
    return count


def copy_edit_log(source_conn, target_conn, ontology_map, run_map, replacements, *, merge_run_id, source_database_id) -> int:
    count = 0
    for row in fetch_all(source_conn, "ontology_edit_log", "edit_id"):
        insert_row(
            target_conn,
            "ontology_edit_log",
            row,
            overrides={
                "edit_id": merged_id("mrg_oedit", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row["edit_id"]),
                "edit_unit_id": merged_id("mrg_oeu", merge_run_id=merge_run_id, source_database_id=source_database_id, source_id=row["edit_unit_id"]),
                "run_id": run_map.get(str(row["run_id"])) if row["run_id"] is not None else None,
                "ontology_id": ontology_map.get(str(row["ontology_id"])) if row["ontology_id"] is not None else None,
                "affected_tables_json": rewrite_json_text(row["affected_tables_json"], replacements),
                "affected_rows_json": rewrite_json_text(row["affected_rows_json"], replacements),
                "before_rows_json": rewrite_json_text(row["before_rows_json"], replacements),
                "after_rows_json": rewrite_json_text(row["after_rows_json"], replacements),
                "verification_report_json": rewrite_json_text(row["verification_report_json"], replacements),
            },
        )
        count += 1
    return count

