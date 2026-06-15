from __future__ import annotations

import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

JsonObject = dict[str, Any]

CANONICAL_ARTIFACT_FOLDERS: tuple[str, ...] = (
    "Input",
    "Corpus",
    "Semantic Release",
    "Documents/logs",
    "Documents/normalized",
    "Documents/originals",
    "Documents/page_images",
    "Documents/raw_extracts",
    "Documents/requests",
    "Documents/structured",
    "Documents/validation",
    "Error Cases",
)

SEMANTIC_RELEASE_RELEASES_DIR = "releases"
SEMANTIC_RELEASE_STAGED_TAXONOMY_DIR = "staged/taxonomy"
SEMANTIC_RELEASE_STAGED_PROJECTIONS_DIR = "staged/projections"
SEMANTIC_RELEASE_INCOMPLETE_MARKER = "incomplete_semantic_release.json"
SEMANTIC_RELEASE_RECEIPTS_DIR = "receipts"

SAFE_DB_STEM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]*$")


def copy_mapping(value: Mapping[str, Any] | None = None) -> JsonObject:
    return deepcopy(dict(value or {}))


def copy_sequence(value: Sequence[Any] | None = None) -> list[Any]:
    return deepcopy(list(value or ()))


def path_text(path: str | os.PathLike[str]) -> str:
    return str(Path(path).resolve(strict=False))


def normalize_database_name(database_name: str) -> str:
    name = str(database_name).strip()
    if name.casefold().endswith(".db"):
        name = name[:-3].strip()
    if not name or name in {".", ".."}:
        raise ValueError("database_name must be a non-empty file stem.")
    if any(separator and separator in name for separator in (os.sep, os.altsep)):
        raise ValueError("database_name must not contain path separators.")
    if not SAFE_DB_STEM_RE.match(name):
        raise ValueError("database_name must be a safe ASCII database file stem.")
    return name
