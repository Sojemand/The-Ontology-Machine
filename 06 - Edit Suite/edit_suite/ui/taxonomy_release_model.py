"""Data helpers for the Semantic Release editor surface."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .. import validation

SCHEMA_VERSION = "taxonomy_release_draft.v1"
MAX_RELEASE_SCAN_DIRECTORIES = 2000
MAX_RELEASE_SCAN_MATCHES = 500
TAXONOMY_SECTIONS = (
    "domains",
    "document_types",
    "categories",
    "subcategories",
    "field_codes",
    "row_types",
    "cell_codes",
    "entity_types",
    "role_types",
    "relation_types",
    "promotion_slots",
)
PROJECTION_LIST_FIELDS = (
    "domain_ids",
    "include_document_types",
    "include_categories",
    "include_subcategories",
    "include_field_codes",
    "include_row_types",
    "include_cell_codes",
)
PROJECTION_TAXONOMY_FIELDS = {
    "domain_ids": "domains",
    "include_document_types": "document_types",
    "include_categories": "categories",
    "include_subcategories": "subcategories",
    "include_field_codes": "field_codes",
    "include_row_types": "row_types",
    "include_cell_codes": "cell_codes",
    "example_document_types": "document_types",
    "party_roles": "role_types",
}
SECTION_ROLE_OPTIONS = (
    "header",
    "summary",
    "body",
    "details",
    "table",
    "line_items",
    "billing",
    "payment",
    "notice",
    "timeline",
    "participants",
    "contact_block",
    "metadata",
    "vision_section",
    "ocr_chunk",
    "form",
    "other",
)
_RELEASE_REQUIRED_KEYS = frozenset({"release_id", "release_version", "master_taxonomy", "projections", "projection_ids", "fingerprint"})
_SCAN_IGNORED_DIRS = frozenset({".git", ".pytest_cache", ".tmp", ".venv", "__pycache__", "dist", "node_modules", "runtime", "venv"})


def _release(frame) -> dict[str, Any]:
    release = frame._draft.setdefault("release", {})
    if not isinstance(release, dict):
        release = {}
        frame._draft["release"] = release
    return release


def _taxonomy_items(frame, section: str) -> list[dict[str, Any]]:
    master = _release(frame).setdefault("master_taxonomy", {})
    if not isinstance(master, dict):
        master = {}
        _release(frame)["master_taxonomy"] = master
    items = master.setdefault(section, [])
    if not isinstance(items, list):
        items = []
        master[section] = items
    return items


def _projections(frame) -> list[dict[str, Any]]:
    projections = _release(frame).setdefault("projections", [])
    if not isinstance(projections, list):
        projections = []
        _release(frame)["projections"] = projections
    return projections


def _scan_release_candidates(root_text: str) -> list[dict[str, Any]]:
    root = Path(root_text).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise ValueError(f"Artifact Tree not found: {root}")
    canonical = root / "Semantic Release" / "releases"
    paths = list(_iter_release_json_paths(root, canonical=canonical))
    candidates: dict[str, dict[str, Any]] = {}
    for path in sorted(paths):
        try:
            release = _read_release(path)
            _require_release_shape(release)
        except Exception:
            continue
        resolved = path.resolve(strict=False)
        relative = resolved.relative_to(root) if _is_relative_to(resolved, root) else resolved
        candidates[str(resolved)] = {
            "path": str(resolved),
            "relative_path": str(relative),
            "release_id": str(release.get("release_id") or ""),
            "release_version": str(release.get("release_version") or ""),
            "fingerprint": str(release.get("fingerprint") or ""),
            "projection_count": len(release.get("projections") or []),
            "canonical": _is_relative_to(resolved, canonical),
        }
    return sorted(candidates.values(), key=lambda item: (not item["canonical"], str(item["relative_path"]).casefold()))


def _iter_release_json_paths(root: Path, *, canonical: Path) -> list[Path]:
    paths: list[Path] = []
    if canonical.is_dir():
        for path in sorted(canonical.glob("*/release.json")):
            paths.append(path)
            if len(paths) >= MAX_RELEASE_SCAN_MATCHES:
                raise ValueError(f"Artifact Tree scan stopped after {MAX_RELEASE_SCAN_MATCHES} release.json files.")
    stack = [root]
    visited_dirs = 0
    while stack:
        current = stack.pop()
        current_resolved = current.resolve(strict=False)
        if _is_relative_to(current_resolved, canonical):
            continue
        visited_dirs += 1
        if visited_dirs > MAX_RELEASE_SCAN_DIRECTORIES:
            raise ValueError(f"Artifact Tree scan stopped after {MAX_RELEASE_SCAN_DIRECTORIES} directories.")
        try:
            with os.scandir(current) as entries:
                child_dirs: list[Path] = []
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False) and entry.name == "release.json":
                            paths.append(Path(entry.path))
                            if len(paths) >= MAX_RELEASE_SCAN_MATCHES:
                                raise ValueError(f"Artifact Tree scan stopped after {MAX_RELEASE_SCAN_MATCHES} release.json files.")
                        elif entry.is_dir(follow_symlinks=False) and entry.name not in _SCAN_IGNORED_DIRS and not entry.name.startswith("."):
                            child_dirs.append(Path(entry.path))
                    except OSError:
                        continue
        except OSError:
            continue
        child_dirs.sort(key=lambda path: path.name.casefold(), reverse=True)
        stack.extend(child_dirs)
    return paths


def _read_release(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("release.json must contain a JSON object.")
    return payload


def _require_release_shape(release: dict[str, Any]) -> None:
    missing = sorted(_RELEASE_REQUIRED_KEYS - set(release))
    if missing:
        raise ValueError(f"Not a complete Semantic Release: {', '.join(missing)}")


def _normalize_draft(payload: dict[str, Any]) -> dict[str, Any]:
    draft = {
        "schema_version": SCHEMA_VERSION,
        "artifact_root": "",
        "release_candidates": [],
        "selected_release_path": "",
        "working_release_path": "",
        "corpus_db_path": "",
        "origin": {},
        "release": {},
        "verification": {"status": "not_loaded", "issues": [], "warnings": []},
    }
    if isinstance(payload, dict):
        draft.update(copy.deepcopy(payload))
    return draft


def _default_working_release_path(artifact_root: str, release: dict[str, Any]) -> str:
    root = Path(artifact_root or ".").expanduser().resolve(strict=False)
    release_id = "".join(char if char.isalnum() or char in "._-" else "_" for char in str(release.get("release_id") or "semantic_release.draft"))
    safe_release_id = validation.safe_filename(release_id.strip("._"), fallback="semantic_release.draft")
    return str(root / "Semantic Release" / "drafts" / "edit_suite" / safe_release_id / "release.json")


def _key_name(section: str) -> str:
    return "id" if section == "domains" else "slot" if section == "promotion_slots" else "code"


def _item_key(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("code") or item.get("slot") or "").strip()


def _csv(value: str) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in str(value or "").replace("\n", ",").split(",") if item.strip()))


def _text_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    return _csv(str(value or ""))


def _truthy_var(variable: Any) -> bool:
    getter = getattr(variable, "get", None)
    return bool(getter()) if callable(getter) else bool(variable)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
