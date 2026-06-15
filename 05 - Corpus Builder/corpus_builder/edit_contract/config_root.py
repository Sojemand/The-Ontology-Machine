"""Raw corpus_config.json root I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import atomic_json_write
from .config_validation import mapping, normalized_path, require_exact_keys, required_bool, required_positive_int, required_text

ROOT_KEYS = ("database", "embeddings", "archive", "fts", "source", "semantic")
SOURCE_FIELDS = (
    "page_images_dir",
    "persist_page_images_in_db",
    "persist_original_artifact_in_db",
    "max_original_artifact_bytes",
    "max_page_image_bytes",
    "max_page_image_total_bytes",
)


def read_root(module_root: Path) -> dict[str, Any]:
    path = module_root / "config" / "corpus_config.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config/corpus_config.json muss ein JSON-Objekt sein.")
    require_exact_keys(payload, ROOT_KEYS, label="corpus_config")
    embeddings = _section(payload, "embeddings", ("dimensions", "batch_size", "max_text_chars"))
    source = _section(payload, "source", SOURCE_FIELDS)
    semantic = _section(payload, "semantic", ("published_release_path", "active_release_path", "release_report_path"))
    return {
        "database": _database_section(payload, module_root),
        "embeddings": _embeddings_section(embeddings),
        "archive": _archive_section(payload),
        "fts": _fts_section(payload),
        "source": _source_section(source, module_root),
        "semantic": _semantic_section(semantic, module_root),
    }


def write_root(module_root: Path, payload: dict[str, Any]) -> None:
    atomic_json_write(module_root / "config" / "corpus_config.json", payload)


def _database_section(payload: dict[str, Any], module_root: Path) -> dict[str, Any]:
    database = _section(payload, "database", ("corpus_db",))
    return {"corpus_db": normalized_path(database["corpus_db"], module_root, "database.corpus_db")}


def _embeddings_section(embeddings: dict[str, Any]) -> dict[str, Any]:
    return {
        "dimensions": required_positive_int(embeddings["dimensions"], field_name="embeddings.dimensions"),
        "batch_size": required_positive_int(embeddings["batch_size"], field_name="embeddings.batch_size"),
        "max_text_chars": required_positive_int(embeddings["max_text_chars"], field_name="embeddings.max_text_chars"),
    }


def _archive_section(payload: dict[str, Any]) -> dict[str, Any]:
    archive = _section(payload, "archive", ("enabled", "keep_archived"))
    return {
        "enabled": required_bool(archive["enabled"], field_name="archive.enabled"),
        "keep_archived": required_bool(archive["keep_archived"], field_name="archive.keep_archived"),
    }


def _fts_section(payload: dict[str, Any]) -> dict[str, Any]:
    fts = _section(payload, "fts", ("enabled", "tokenizer"))
    return {
        "enabled": required_bool(fts["enabled"], field_name="fts.enabled"),
        "tokenizer": required_text(fts["tokenizer"], field_name="fts.tokenizer"),
    }


def _source_section(source: dict[str, Any], module_root: Path) -> dict[str, Any]:
    return {
        "page_images_dir": normalized_path(source["page_images_dir"], module_root, "source.page_images_dir", allow_empty=True),
        "persist_page_images_in_db": required_bool(source["persist_page_images_in_db"], field_name="source.persist_page_images_in_db"),
        "persist_original_artifact_in_db": required_bool(source["persist_original_artifact_in_db"], field_name="source.persist_original_artifact_in_db"),
        "max_original_artifact_bytes": required_positive_int(source["max_original_artifact_bytes"], field_name="source.max_original_artifact_bytes"),
        "max_page_image_bytes": required_positive_int(source["max_page_image_bytes"], field_name="source.max_page_image_bytes"),
        "max_page_image_total_bytes": required_positive_int(source["max_page_image_total_bytes"], field_name="source.max_page_image_total_bytes"),
    }


def _semantic_section(semantic: dict[str, Any], module_root: Path) -> dict[str, Any]:
    return {
        "published_release_path": normalized_path(
            semantic["published_release_path"],
            module_root,
            "semantic.published_release_path",
        ),
        "active_release_path": normalized_path(semantic["active_release_path"], module_root, "semantic.active_release_path"),
        "release_report_path": normalized_path(semantic["release_report_path"], module_root, "semantic.release_report_path"),
    }


def _section(payload: dict[str, Any], name: str, expected: tuple[str, ...]) -> dict[str, Any]:
    section = mapping(payload.get(name), label=f"corpus_config.{name}")
    require_exact_keys(section, expected, label=f"corpus_config.{name}")
    return section
