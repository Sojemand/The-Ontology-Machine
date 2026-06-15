"""Raw corpus-config helpers for edit-contract surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_root import read_root, write_root
from .config_validation import validate_embeddings_surface, validate_settings_surface


def read_settings(module_root: Path) -> dict[str, Any]:
    return _settings_from_root(read_root(module_root))


def read_embeddings(module_root: Path) -> dict[str, Any]:
    return _embeddings_from_root(read_root(module_root))


def read_config_surfaces(module_root: Path) -> dict[str, dict[str, Any]]:
    payload = read_root(module_root)
    return {
        "settings": _settings_from_root(payload),
        "embeddings": _embeddings_from_root(payload),
    }


def _settings_from_root(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "database.corpus_db": payload["database"]["corpus_db"],
        "archive.enabled": payload["archive"]["enabled"],
        "archive.keep_archived": payload["archive"]["keep_archived"],
        "fts.enabled": payload["fts"]["enabled"],
        "fts.tokenizer": payload["fts"]["tokenizer"],
        "source.page_images_dir": payload["source"]["page_images_dir"],
        "source.persist_page_images_in_db": payload["source"]["persist_page_images_in_db"],
        "semantic.published_release_path": payload["semantic"]["published_release_path"],
        "semantic.active_release_path": payload["semantic"]["active_release_path"],
        "semantic.release_report_path": payload["semantic"]["release_report_path"],
    }


def write_settings(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_settings_surface(payload, module_root=module_root)
    current = read_root(module_root)
    write_root(
        module_root,
        {
            "database": {"corpus_db": validated["database.corpus_db"]},
            "embeddings": dict(current["embeddings"]),
            "archive": {
                "enabled": validated["archive.enabled"],
                "keep_archived": validated["archive.keep_archived"],
            },
            "fts": {
                "enabled": validated["fts.enabled"],
                "tokenizer": validated["fts.tokenizer"],
            },
            "source": {
                **dict(current["source"]),
                "page_images_dir": validated["source.page_images_dir"],
                "persist_page_images_in_db": validated["source.persist_page_images_in_db"],
            },
            "semantic": {
                "published_release_path": validated["semantic.published_release_path"],
                "active_release_path": validated["semantic.active_release_path"],
                "release_report_path": validated["semantic.release_report_path"],
            },
        },
    )
    return read_settings(module_root)


def _embeddings_from_root(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "embeddings.dimensions": payload["embeddings"]["dimensions"],
        "embeddings.batch_size": payload["embeddings"]["batch_size"],
        "embeddings.max_text_chars": payload["embeddings"]["max_text_chars"],
    }


def write_embeddings(module_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_embeddings_surface(payload)
    current = read_root(module_root)
    write_root(
        module_root,
        {
            "database": dict(current["database"]),
            "embeddings": {
                "dimensions": validated["embeddings.dimensions"],
                "batch_size": validated["embeddings.batch_size"],
                "max_text_chars": validated["embeddings.max_text_chars"],
            },
            "archive": dict(current["archive"]),
            "fts": dict(current["fts"]),
            "source": dict(current["source"]),
            "semantic": dict(current["semantic"]),
        },
    )
    return read_embeddings(module_root)


__all__ = [
    "read_config_surfaces",
    "read_embeddings",
    "read_settings",
    "validate_embeddings_surface",
    "validate_settings_surface",
    "write_embeddings",
    "write_settings",
]
