from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.models import load_config


def test_load_config_coerces_scalars_and_defaults_invalid_values(tmp_path: Path):
    config_path = tmp_path / "config" / "corpus_config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "database": {"corpus_db": "./output/corpus.db"},
                "embeddings": {
                    "dimensions": "bad",
                    "batch_size": "25",
                    "max_text_chars": "6000",
                },
                "archive": {"enabled": "1", "keep_archived": "0"},
                "fts": {"enabled": "true", "tokenizer": 77},
                "source": {
                    "page_images_dir": 123,
                    "persist_page_images_in_db": "1",
                    "persist_original_artifact_in_db": "1",
                    "max_original_artifact_bytes": "bad",
                    "max_page_image_bytes": "42",
                    "max_page_image_total_bytes": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path, module_root=tmp_path)

    assert config.database.corpus_db == str((tmp_path / "output" / "corpus.db").resolve())
    assert config.embeddings.dimensions == 1536
    assert config.embeddings.batch_size == 25
    assert config.embeddings.max_text_chars == 6000
    assert config.archive.enabled is True
    assert config.archive.keep_archived is False
    assert config.fts.enabled is True
    assert config.fts.tokenizer == "unicode61"
    assert config.source.page_images_dir == ""
    assert config.source.persist_page_images_in_db is True
    assert config.source.persist_original_artifact_in_db is True
    assert config.source.max_original_artifact_bytes == 52428800
    assert config.source.max_page_image_bytes == 42
    assert config.source.max_page_image_total_bytes == 104857600


def test_committed_config_uses_portable_defaults_and_safety_limits() -> None:
    module_root = Path(__file__).resolve().parents[2]
    payload = json.loads((module_root / "config" / "corpus_config.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload)

    assert payload["database"]["corpus_db"] == "./output/corpus.db"
    assert "C:\\Users\\" not in serialized
    assert payload["source"]["persist_original_artifact_in_db"] is False
    assert payload["source"]["max_original_artifact_bytes"] == 52428800
    assert payload["source"]["max_page_image_bytes"] == 10485760
    assert payload["source"]["max_page_image_total_bytes"] == 104857600
