"""Evidence indexing and linking helpers for semantic materialization."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from typing import Any, Iterable

from .types import JsonDict

SUBJECT_DOCUMENT_ENTITY = "document_entity"
SUBJECT_ENTITY_ATTRIBUTE = "entity_attribute"
SUBJECT_ENTITY_RELATION = "entity_relation"

_FIELD_PATH_RE = re.compile(r"^content\.fields\.([^.\[\]]+)(?:\.|\[|$)")
_ROW_PATH_RE = re.compile(r"^content\.rows\[(\d+)\](?:\.|\[|$)")
_SEGMENT_PATH_RE = re.compile(r"^content\.segments\[(\d+)\](?:\.|\[|$)")
_RELATION_PATH_RE = re.compile(r"^relations\[(\d+)\](?:\.|\[|$)")


def build_semantic_evidence_index(conn: sqlite3.Connection, document_id: str) -> JsonDict:
    path_atom_ids: dict[str, list[int]] = defaultdict(list)
    source_ref_atom_ids: dict[str, list[int]] = defaultdict(list)
    anchor_atom_ids: dict[tuple[str, str], list[int]] = defaultdict(list)
    rows = conn.execute(
        "SELECT atom_id, json_path, source_ref, anchor_kind, anchor_key FROM evidence_atoms WHERE document_id = ?",
        (document_id,),
    ).fetchall()
    for atom in rows:
        atom_id = int(atom["atom_id"])
        path_atom_ids[str(atom["json_path"] or "")].append(atom_id)
        if atom["source_ref"]:
            source_ref_atom_ids[str(atom["source_ref"])].append(atom_id)
        if atom["anchor_kind"] and atom["anchor_key"]:
            anchor_atom_ids[(str(atom["anchor_kind"]), str(atom["anchor_key"]))].append(atom_id)
    return {"paths": path_atom_ids, "source_refs": source_ref_atom_ids, "anchors": anchor_atom_ids}


def _insert_semantic_evidence_links(
    conn: sqlite3.Connection,
    subject_kind: str,
    subject_id: int,
    atom_ids: Iterable[int],
    evidence_role: str,
) -> None:
    for atom_id in sorted(set(int(atom_id) for atom_id in atom_ids)):
        conn.execute(
            "INSERT OR IGNORE INTO semantic_evidence_links (subject_kind, subject_id, atom_id, evidence_role) VALUES (?, ?, ?, ?)",
            (subject_kind, subject_id, atom_id, evidence_role),
        )


def _semantic_atom_ids(
    subject: JsonDict,
    evidence_index: JsonDict | None,
    *,
    include_prefix: bool,
    entity_key: str | None = None,
) -> list[int]:
    if not evidence_index:
        return []
    source_path = subject.get("source_path")
    path_values = [str(source_path)] if source_path not in (None, "") else []
    path_values.extend(str(value) for value in _iter_evidence_values(subject.get("evidence_refs")) if _looks_like_json_path(str(value)))
    source_ref_values = [str(value) for value in _iter_evidence_values(subject.get("evidence_refs")) if not _looks_like_json_path(str(value))]
    atom_ids = _atom_ids_for_paths(evidence_index, path_values, include_prefix=include_prefix)
    atom_ids.extend(_atom_ids_for_source_refs(evidence_index, source_ref_values))
    anchor = _anchor_for_subject(str(source_path or ""), entity_key=entity_key)
    if include_prefix and anchor is not None:
        atom_ids.extend(evidence_index.get("anchors", {}).get(anchor, []))
    return sorted(set(atom_ids))


def _atom_ids_for_paths(evidence_index: JsonDict, paths: Iterable[str], *, include_prefix: bool) -> list[int]:
    atom_ids: list[int] = []
    path_atom_ids = evidence_index.get("paths", {})
    for path in paths:
        if not path:
            continue
        atom_ids.extend(path_atom_ids.get(path, []))
        if include_prefix:
            dotted_prefix = f"{path}."
            indexed_prefix = f"{path}["
            for atom_path, ids in path_atom_ids.items():
                if str(atom_path).startswith(dotted_prefix) or str(atom_path).startswith(indexed_prefix):
                    atom_ids.extend(ids)
    return atom_ids


def _atom_ids_for_source_refs(evidence_index: JsonDict, refs: Iterable[str]) -> list[int]:
    atom_ids: list[int] = []
    source_ref_atom_ids = evidence_index.get("source_refs", {})
    for ref in refs:
        if ref:
            atom_ids.extend(source_ref_atom_ids.get(ref, []))
    return atom_ids


def _iter_evidence_values(value: Any) -> Iterable[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                return list(_iter_evidence_values(json.loads(stripped)))
            except json.JSONDecodeError:
                return [stripped]
        return [stripped]
    if isinstance(value, dict):
        values: list[Any] = []
        for child in value.values():
            values.extend(_iter_evidence_values(child))
        return values
    if isinstance(value, list):
        values: list[Any] = []
        for child in value:
            values.extend(_iter_evidence_values(child))
        return values
    return [value]


def _looks_like_json_path(value: str) -> bool:
    return bool(value.startswith(("content.", "context.", "classification.", "projection.", "relations[", "source.", "processing.")))


def _anchor_for_subject(source_path: str, *, entity_key: str | None = None) -> tuple[str, str] | None:
    if entity_key and entity_key.startswith("segment:"):
        return "segment", entity_key
    field = _FIELD_PATH_RE.match(source_path)
    if field and field.group(1) != "_source_refs":
        return "field", f"field:{field.group(1)}"
    row = _ROW_PATH_RE.match(source_path)
    if row:
        return "row", f"row:{row.group(1)}"
    segment = _SEGMENT_PATH_RE.match(source_path)
    if segment:
        return "segment", f"segment:{segment.group(1)}"
    relation = _RELATION_PATH_RE.match(source_path)
    if relation:
        return "relation", f"relation:{relation.group(1)}"
    return None


def _delete_materialized_semantic_evidence_links(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute(
        "DELETE FROM semantic_evidence_links WHERE subject_kind = ? AND subject_id IN ("
        "SELECT relation_id FROM entity_relations WHERE document_id = ? "
        "AND (relation_origin = 'materialized' OR status = 'materialized' OR created_by = 'semantic_release' "
        "OR source_entity_id IN (SELECT entity_id FROM document_entities WHERE document_id = ? AND state = 'materialized') "
        "OR target_entity_id IN (SELECT entity_id FROM document_entities WHERE document_id = ? AND state = 'materialized'))"
        ")",
        (SUBJECT_ENTITY_RELATION, document_id, document_id, document_id),
    )
    conn.execute(
        "DELETE FROM semantic_evidence_links WHERE subject_kind = ? AND subject_id IN ("
        "SELECT attribute_id FROM entity_attributes WHERE entity_id IN ("
        "SELECT entity_id FROM document_entities WHERE document_id = ? AND state = 'materialized'))",
        (SUBJECT_ENTITY_ATTRIBUTE, document_id),
    )
    conn.execute(
        "DELETE FROM semantic_evidence_links WHERE subject_kind = ? AND subject_id IN ("
        "SELECT entity_id FROM document_entities WHERE document_id = ? AND state = 'materialized')",
        (SUBJECT_DOCUMENT_ENTITY, document_id),
    )


def _sqlite_safe(value: Any) -> Any:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
