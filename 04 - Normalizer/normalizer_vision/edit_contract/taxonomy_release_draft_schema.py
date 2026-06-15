from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..models.serialization import utc_now_iso

SCHEMA_VERSION = "taxonomy_release_draft.v1"
SURFACE_ID = "normalizer.taxonomy_release_draft"
MODULE_DRAFT_PATH = Path("output") / "edit_suite" / "taxonomy_release_draft.json"
RELEASE_REQUIRED_KEYS = frozenset(
    {
        "release_id",
        "release_version",
        "master_taxonomy",
        "projections",
        "projection_ids",
        "fingerprint",
    }
)


def empty_draft() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_root": "",
        "release_candidates": [],
        "selected_release_path": "",
        "working_release_path": "",
        "corpus_db_path": "",
        "origin": {},
        "release": {},
        "verification": verification("not_loaded", issues=["Select an Artifact Tree and load a Semantic Release copy."]),
    }


def normalize_draft(payload: dict[str, Any]) -> dict[str, Any]:
    draft = empty_draft()
    draft.update({key: copy.deepcopy(value) for key, value in payload.items() if key in draft or key in {"editor_state"}})
    draft["schema_version"] = SCHEMA_VERSION
    if not isinstance(draft.get("release_candidates"), list):
        draft["release_candidates"] = []
    if not isinstance(draft.get("origin"), dict):
        draft["origin"] = {}
    if not isinstance(draft.get("release"), dict):
        draft["release"] = {}
    if not isinstance(draft.get("verification"), dict):
        draft["verification"] = verification("not_loaded")
    return draft


def verification(status: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "status": status,
        "issues": [],
        "warnings": [],
        "verified_at": None,
    }
    payload.update(extra)
    if status == "verified":
        payload["verified_at"] = utc_now_iso()
    return payload
