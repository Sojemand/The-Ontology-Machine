"""Compiled Semantic Release draft workflow for taxonomy/projection editing."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..models.serialization import atomic_json_write
from .taxonomy_release_draft_db import _connect_corpus_db_readonly, db_update_decision
from .taxonomy_release_draft_io import (
    default_working_release_path,
    find_release_candidates,
    load_release_copy,
    working_release_path,
)
from .taxonomy_release_draft_schema import (
    MODULE_DRAFT_PATH,
    SCHEMA_VERSION,
    SURFACE_ID,
    empty_draft,
    normalize_draft,
)
from .taxonomy_release_draft_verification import master_core_signature, verify_release


def read_draft(module_root: Path) -> dict[str, Any]:
    path = module_root / MODULE_DRAFT_PATH
    if not path.exists():
        return empty_draft()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return empty_draft()
    if not isinstance(payload, dict):
        return empty_draft()
    return normalize_draft(payload)


def write_draft(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    draft = validate_draft(module_root, payload)
    release = dict(draft["release"])
    target = working_release_path(draft)
    atomic_json_write(target, release)
    draft["working_release_path"] = str(target)
    draft["verification"]["working_copy_written"] = True
    draft["verification"]["working_release_path"] = str(target)
    atomic_json_write(module_root / MODULE_DRAFT_PATH, draft)
    return draft


def validate_draft(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    del module_root
    draft = normalize_draft(payload)
    release = draft.get("release")
    if not isinstance(release, dict) or not release:
        raise ValueError("Kein Semantic Release geladen. Bitte zuerst eine release.json als Kopie laden.")
    origin = dict(draft.get("origin") or {})
    verified_release, verification = verify_release(release, origin=origin, corpus_db_path=draft.get("corpus_db_path"))
    draft["release"] = verified_release
    draft["verification"] = verification
    if not str(draft.get("working_release_path") or "").strip():
        draft["working_release_path"] = str(default_working_release_path(draft))
    return draft


__all__ = [
    "SCHEMA_VERSION",
    "SURFACE_ID",
    "_connect_corpus_db_readonly",
    "db_update_decision",
    "default_working_release_path",
    "empty_draft",
    "find_release_candidates",
    "load_release_copy",
    "master_core_signature",
    "read_draft",
    "validate_draft",
    "verify_release",
    "write_draft",
]
