"""Initial semantic release alignment helpers."""

from __future__ import annotations

import json
from typing import Any


def align_initial_activation_payload_headers(
    conn,
    release: dict[str, Any],
    *,
    current_snapshot: dict[str, Any] | None,
) -> int:
    if current_snapshot is not None or not _table_exists(conn, "document_payloads"):
        return 0
    if not _table_exists(conn, "document_processing_state"):
        return 0
    projections = {
        str(item.get("projection_id") or "").strip(): dict(item)
        for item in release.get("projections", []) or []
        if isinstance(item, dict) and str(item.get("projection_id") or "").strip()
    }
    if not projections:
        return 0
    rows = conn.execute(
        "SELECT d.id, dps.projection_id, dp.projection_json "
        "FROM documents d "
        "JOIN document_processing_state dps ON dps.document_id = d.id "
        "JOIN document_payloads dp ON dp.document_id = d.id "
        "WHERE COALESCE(d.is_archived, 0) = 0"
    ).fetchall()
    aligned = 0
    for row in rows:
        projection_id = str(row["projection_id"] or "").strip()
        projection = projections.get(projection_id)
        if projection is None:
            continue
        projection_json = _json_object(row["projection_json"])
        projection_json["projection_id"] = projection_id
        projection_json["projection_fingerprint"] = str(projection.get("projection_fingerprint") or "")
        projection_json["master_taxonomy_id"] = str(release.get("master_taxonomy_id") or "")
        projection_json["master_taxonomy_version"] = str(release.get("master_taxonomy_version") or "")
        conn.execute(
            "UPDATE document_payloads SET release_fingerprint = ?, projection_json = ? WHERE document_id = ?",
            (
                str(release.get("fingerprint") or ""),
                json.dumps(projection_json, ensure_ascii=False, sort_keys=True),
                str(row["id"] or ""),
            ),
        )
        aligned += 1
    return aligned


def _json_object(raw_value: Any) -> dict[str, Any]:
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return dict(value) if isinstance(value, dict) else {}
    return {}


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None
