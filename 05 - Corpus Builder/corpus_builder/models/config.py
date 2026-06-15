"""Config loading and path normalization for the Corpus Builder surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .coercion import _coerce_bool, _coerce_int, _coerce_text
from .types import (
    ArchiveConfig,
    CorpusConfig,
    DatabaseConfig,
    EmbeddingConfig,
    FTSConfig,
    SemanticConfig,
    SourceConfig,
)


def load_config(config_path: Path, *, module_root: Path | None = None) -> CorpusConfig:
    config_path = Path(config_path)
    resolved_root = (
        Path(module_root).resolve()
        if module_root is not None
        else config_path.parent.parent.resolve()
    )
    defaults = CorpusConfig()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Corpus Config fehlt: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corpus Config ist kein gueltiges JSON: {config_path}") from exc
    except OSError as exc:
        raise ValueError(f"Corpus Config kann nicht gelesen werden: {config_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Corpus Config muss ein JSON-Objekt sein.")

    database = _database_section(payload)

    def _section(name: str) -> dict[str, Any]:
        value = payload.get(name, {})
        return value if isinstance(value, dict) else {}

    embeddings = _section("embeddings")
    archive = _section("archive")
    fts = _section("fts")
    source = _section("source")
    semantic = _section("semantic")

    config = CorpusConfig(
        database=DatabaseConfig(
            corpus_db=_coerce_text(
                database.get("corpus_db"),
                defaults.database.corpus_db,
            ),
        ),
        embeddings=EmbeddingConfig(
            dimensions=_coerce_int(
                embeddings.get("dimensions"),
                defaults.embeddings.dimensions,
                minimum=1,
            ),
            batch_size=_coerce_int(
                embeddings.get("batch_size"),
                defaults.embeddings.batch_size,
                minimum=1,
            ),
            max_text_chars=_coerce_int(
                embeddings.get("max_text_chars"),
                defaults.embeddings.max_text_chars,
                minimum=1,
            ),
        ),
        archive=ArchiveConfig(
            enabled=_coerce_bool(archive.get("enabled"), defaults.archive.enabled),
            keep_archived=_coerce_bool(
                archive.get("keep_archived"),
                defaults.archive.keep_archived,
            ),
        ),
        fts=FTSConfig(
            enabled=_coerce_bool(fts.get("enabled"), defaults.fts.enabled),
            tokenizer=_coerce_text(fts.get("tokenizer"), defaults.fts.tokenizer),
        ),
        source=SourceConfig(
            page_images_dir=_coerce_text(
                source.get("page_images_dir"),
                defaults.source.page_images_dir,
            ),
            persist_page_images_in_db=_coerce_bool(
                source.get("persist_page_images_in_db"),
                defaults.source.persist_page_images_in_db,
            ),
            persist_original_artifact_in_db=_coerce_bool(
                source.get("persist_original_artifact_in_db"),
                defaults.source.persist_original_artifact_in_db,
            ),
            max_original_artifact_bytes=_coerce_int(
                source.get("max_original_artifact_bytes"),
                defaults.source.max_original_artifact_bytes,
                minimum=1,
            ),
            max_page_image_bytes=_coerce_int(
                source.get("max_page_image_bytes"),
                defaults.source.max_page_image_bytes,
                minimum=1,
            ),
            max_page_image_total_bytes=_coerce_int(
                source.get("max_page_image_total_bytes"),
                defaults.source.max_page_image_total_bytes,
                minimum=1,
            ),
        ),
        semantic=SemanticConfig(
            published_release_path=_coerce_text(
                semantic.get("published_release_path"),
                defaults.semantic.published_release_path,
            ),
            active_release_path=_coerce_text(
                semantic.get("active_release_path"),
                defaults.semantic.active_release_path,
            ),
            release_report_path=_coerce_text(
                semantic.get("release_report_path"),
                defaults.semantic.release_report_path,
            ),
        ),
    )
    return _normalize_config_paths(config, resolved_root)


def _database_section(payload: dict[str, Any]) -> dict[str, Any]:
    if "database" not in payload:
        raise ValueError("Corpus Config enthaelt fehlende Sektion: database.")
    database = payload.get("database")
    if not isinstance(database, dict):
        raise ValueError("Corpus Config database muss ein JSON-Objekt sein.")
    corpus_db = database.get("corpus_db")
    if not isinstance(corpus_db, str) or not corpus_db.strip():
        raise ValueError("Corpus Config database.corpus_db muss ein nichtleerer Textpfad sein.")
    return database


def _normalize_config_paths(config: CorpusConfig, module_root: Path) -> CorpusConfig:
    config.database.corpus_db = _resolve_config_path(
        config.database.corpus_db,
        module_root,
    )
    if config.source.page_images_dir:
        config.source.page_images_dir = _resolve_config_path(
            config.source.page_images_dir,
            module_root,
        )
    config.semantic.published_release_path = _resolve_config_path(
        config.semantic.published_release_path,
        module_root,
    )
    config.semantic.active_release_path = _resolve_config_path(
        config.semantic.active_release_path,
        module_root,
    )
    config.semantic.release_report_path = _resolve_config_path(
        config.semantic.release_report_path,
        module_root,
    )
    return config


def _resolve_config_path(raw_path: str, module_root: Path) -> str:
    text = str(raw_path or "").strip()
    if not text:
        return ""
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = module_root / path
    return str(path.resolve())
