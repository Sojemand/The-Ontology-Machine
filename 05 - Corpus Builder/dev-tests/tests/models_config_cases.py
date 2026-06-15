from __future__ import annotations

import json
from pathlib import Path

import pytest

from corpus_builder.models import EmbeddingRequest, EmbeddingRuntimeSettings, load_config


def test_load_config_rejects_non_object_root(tmp_path: Path):
    config_path = tmp_path / "config" / "corpus_config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON-Objekt"):
        load_config(config_path, module_root=tmp_path)


def test_load_config_rejects_missing_or_malformed_database_section(tmp_path: Path):
    config_path = tmp_path / "config" / "corpus_config.json"
    config_path.parent.mkdir(parents=True)

    for payload, error in (
        ({}, "database"),
        ({"database": []}, "database muss ein JSON-Objekt"),
        ({"database": {"corpus_db": 123}}, "database.corpus_db"),
    ):
        config_path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match=error):
            load_config(config_path, module_root=tmp_path)


def test_load_config_rejects_malformed_or_missing_config_file(tmp_path: Path):
    config_path = tmp_path / "config" / "corpus_config.json"
    config_path.parent.mkdir(parents=True)

    with pytest.raises(ValueError, match="fehlt"):
        load_config(config_path, module_root=tmp_path)

    config_path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="gueltiges JSON"):
        load_config(config_path, module_root=tmp_path)


def test_load_config_resolves_relative_paths_against_module_root(tmp_path: Path):
    config_path = tmp_path / "config" / "corpus_config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "database": {"corpus_db": "./data/corpus.db"},
                "source": {
                    "page_images_dir": "./assets/page_images",
                    "persist_page_images_in_db": True,
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path, module_root=tmp_path)

    assert config.database.corpus_db == str((tmp_path / "data" / "corpus.db").resolve())
    assert config.source.page_images_dir == str((tmp_path / "assets" / "page_images").resolve())
    assert config.source.persist_page_images_in_db is True
    assert config.source.persist_original_artifact_in_db is False
    assert config.source.max_original_artifact_bytes == 52428800
    assert config.source.max_page_image_bytes == 10485760
    assert config.source.max_page_image_total_bytes == 104857600


def test_embedding_request_requires_runtime_settings() -> None:
    request = EmbeddingRequest(
        corpus_db_path="C:/tmp/corpus.db",
        runtime_settings=EmbeddingRuntimeSettings(model="text-embedding-3-small"),
    )

    assert request.corpus_db_path == "C:/tmp/corpus.db"
    assert request.runtime_settings.model == "text-embedding-3-small"
