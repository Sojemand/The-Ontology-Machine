"""Backfill helpers for schema-era compatibility columns."""

from __future__ import annotations

import re
import sqlite3

_FIELD_SOURCE_REF_RE = re.compile(r"^content\.fields\._source_refs\.([^.\[\]]+)\[\d+\]$")
_FIELD_PATH_RE = re.compile(r"^content\.fields\.([^.\[\]]+)(?:\.|\[|$)")
_ROW_PATH_RE = re.compile(r"^content\.rows\[(\d+)\](?:\.|\[|$)")
_SEGMENT_PATH_RE = re.compile(r"^content\.segments\[(\d+)\](?:\.|\[|$)")
_RELATION_PATH_RE = re.compile(r"^relations\[(\d+)\](?:\.|\[|$)")


def anchor_from_json_path(json_path: str) -> tuple[str, str] | None:
    field_source_ref = _FIELD_SOURCE_REF_RE.match(json_path)
    if field_source_ref:
        field_name = field_source_ref.group(1)
        return "field", f"field:{field_name}"
    field = _FIELD_PATH_RE.match(json_path)
    if field and field.group(1) != "_source_refs":
        field_name = field.group(1)
        return "field", f"field:{field_name}"
    row = _ROW_PATH_RE.match(json_path)
    if row:
        row_index = row.group(1)
        return "row", f"row:{row_index}"
    segment = _SEGMENT_PATH_RE.match(json_path)
    if segment:
        segment_index = segment.group(1)
        return "segment", f"segment:{segment_index}"
    relation = _RELATION_PATH_RE.match(json_path)
    if relation:
        relation_index = relation.group(1)
        return "relation", f"relation:{relation_index}"
    return None


def backfill_evidence_anchors(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT atom_id, json_path FROM evidence_atoms "
        "WHERE anchor_kind IS NULL OR anchor_kind = '' OR anchor_key IS NULL OR anchor_key = ''"
    ).fetchall()
    for row in rows:
        anchor = anchor_from_json_path(str(row["json_path"] or ""))
        if anchor is None:
            continue
        conn.execute(
            "UPDATE evidence_atoms SET anchor_kind = ?, anchor_key = ? WHERE atom_id = ?",
            (anchor[0], anchor[1], row["atom_id"]),
        )


def backfill_candidate_layers(conn: sqlite3.Connection) -> None:
    conn.execute(
        "UPDATE slot_candidates SET candidate_layer = 'release' "
        "WHERE COALESCE(candidate_layer, 'base') = 'base' "
        "AND (COALESCE(is_projection_backed, 0) != 0 "
        "OR strategy LIKE 'release_%' "
        "OR strategy LIKE 'projection_%' "
        "OR strategy LIKE 'projection:%' "
        "OR origin_kind LIKE 'release%' "
        "OR origin_kind LIKE 'projection%')"
    )
    conn.execute(
        "UPDATE slot_candidates SET candidate_layer = 'base' "
        "WHERE candidate_layer IS NULL OR candidate_layer = ''"
    )
    conn.execute(
        "UPDATE slot_candidates SET candidate_origin = COALESCE(NULLIF(candidate_origin, ''), NULLIF(origin_kind, ''), NULLIF(strategy, ''), 'unknown') "
        "WHERE candidate_origin IS NULL OR candidate_origin = ''"
    )
