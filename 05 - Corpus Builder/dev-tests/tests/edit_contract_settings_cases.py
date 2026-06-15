from __future__ import annotations

import json
from pathlib import Path

from .edit_contract_support import _copy_module, _invoke_contract


def test_settings_write_roundtrip_preserves_embeddings_subtree(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    before = json.loads((module_root / "config" / "corpus_config.json").read_text(encoding="utf-8"))

    response = _invoke_contract(
        module_root,
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "corpus_builder.settings",
            "value": {
                "database.corpus_db": "./output/custom.corpus.db",
                "archive.enabled": False,
                "archive.keep_archived": False,
                "fts.enabled": False,
                "fts.tokenizer": "porter",
                "source.page_images_dir": "./output/page_images",
                "source.persist_page_images_in_db": True,
                "semantic.published_release_path": "./config/semantic_release.default.json",
                "semantic.active_release_path": "./state/semantic_release.active.json",
                "semantic.release_report_path": "./state/semantic_release_report.json",
            },
        },
    )

    after = json.loads((module_root / "config" / "corpus_config.json").read_text(encoding="utf-8"))
    assert response["status"] == "ok"
    assert response["value"]["database.corpus_db"] == "./output/custom.corpus.db"
    assert response["value"]["source.page_images_dir"] == "./output/page_images"
    assert after["embeddings"] == before["embeddings"]
    assert after["database"]["corpus_db"] == "./output/custom.corpus.db"
    assert after["archive"] == {"enabled": False, "keep_archived": False}
    assert after["fts"] == {"enabled": False, "tokenizer": "porter"}
    expected_source = dict(before["source"])
    expected_source.update({"page_images_dir": "./output/page_images", "persist_page_images_in_db": True})
    assert after["source"] == expected_source


def test_settings_write_accepts_absolute_corpus_db_path(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    external_db = (tmp_path / "artefacts" / "Corpus" / "housing-2026-04-05-corpus-en.db").resolve()

    response = _invoke_contract(
        module_root,
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "corpus_builder.settings",
            "value": {
                "database.corpus_db": str(external_db),
                "archive.enabled": True,
                "archive.keep_archived": True,
                "fts.enabled": True,
                "fts.tokenizer": "unicode61",
                "source.page_images_dir": "",
                "source.persist_page_images_in_db": False,
                "semantic.published_release_path": "./config/semantic_release.default.json",
                "semantic.active_release_path": "./state/semantic_release.active.json",
                "semantic.release_report_path": "./state/semantic_release_report.json",
            },
        },
    )

    after = json.loads((module_root / "config" / "corpus_config.json").read_text(encoding="utf-8"))
    assert response["status"] == "ok"
    assert response["value"]["database.corpus_db"] == str(external_db)
    assert after["database"]["corpus_db"] == str(external_db)


def test_embeddings_write_roundtrip_preserves_other_config_subtrees(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)
    before = json.loads((module_root / "config" / "corpus_config.json").read_text(encoding="utf-8"))

    response = _invoke_contract(
        module_root,
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "corpus_builder.embeddings_policy",
            "value": {
                "embeddings.dimensions": 3072,
                "embeddings.batch_size": 25,
                "embeddings.max_text_chars": 16000,
            },
        },
    )

    after = json.loads((module_root / "config" / "corpus_config.json").read_text(encoding="utf-8"))
    assert response["status"] == "ok"
    assert response["value"] == {
        "embeddings.dimensions": 3072,
        "embeddings.batch_size": 25,
        "embeddings.max_text_chars": 16000,
    }
    assert after["embeddings"] == {"dimensions": 3072, "batch_size": 25, "max_text_chars": 16000}
    assert after["database"] == before["database"]
    assert after["archive"] == before["archive"]
    assert after["fts"] == before["fts"]
    assert after["source"] == before["source"]
    assert after["semantic"] == before["semantic"]
