"""Candidate-to-evidence linking helpers for loader materialization."""

from __future__ import annotations

import sqlite3

from . import repository
from .types import JsonDict


def link_candidate_evidence(
    conn: sqlite3.Connection,
    candidate_id: int,
    candidate: JsonDict,
    path_atom_ids: dict[str, list[int]],
    source_ref_atom_ids: dict[str, list[int]],
) -> None:
    linked = {atom_id for path in candidate.get("evidence_paths") or [] for atom_id in path_atom_ids.get(str(path), [])}
    if not linked:
        linked = {atom_id for source_ref in candidate.get("source_refs") or [] for atom_id in source_ref_atom_ids.get(str(source_ref), [])}
    for atom_id in sorted(linked):
        repository.insert_candidate_evidence(conn, candidate_id, atom_id)
