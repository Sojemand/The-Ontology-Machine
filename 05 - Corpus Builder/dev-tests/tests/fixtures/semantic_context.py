"""Semantic-release service context factory for tests."""

from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.context import ModuleContext

MODULE_ROOT = Path(__file__).resolve().parents[3]


def make_semantic_context(tmp_path: Path) -> ModuleContext:
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    context.config_dir.mkdir(parents=True, exist_ok=True)
    release_source = MODULE_ROOT / "config" / "semantic_release.default.json"
    search_policy_source = MODULE_ROOT / "config" / "search_policy.json"
    release_text = release_source.read_text(encoding="utf-8")
    (context.config_dir / "semantic_release.default.json").write_text(release_text, encoding="utf-8")
    (context.config_dir / "search_policy.json").write_text(search_policy_source.read_text(encoding="utf-8"), encoding="utf-8")
    (context.state_dir / "semantic_release.active.json").write_text(release_text, encoding="utf-8")
    (context.config_dir / "corpus_config.json").write_text(
        json.dumps(
            {
                "database": {"corpus_db": "./output/test.corpus.db"},
                "embeddings": {
                    "dimensions": 1536,
                    "batch_size": 50,
                    "max_text_chars": 12000,
                },
                "archive": {
                    "enabled": True,
                    "keep_archived": True,
                },
                "fts": {
                    "enabled": True,
                    "tokenizer": "unicode61",
                },
                "source": {
                    "page_images_dir": "",
                    "persist_page_images_in_db": False,
                },
                "semantic": {
                    "published_release_path": "./config/semantic_release.default.json",
                    "active_release_path": "./state/semantic_release.active.json",
                    "release_report_path": "./state/semantic_release_report.json",
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return context


__all__ = ["make_semantic_context"]
