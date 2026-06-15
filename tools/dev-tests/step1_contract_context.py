from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from corpus_builder.context import ModuleContext

from step1_contract_paths import BASELINE, CORPUS_ROOT


def make_semantic_context(base_dir: Path) -> ModuleContext:
    context = ModuleContext(base_dir)
    context.ensure_runtime_dirs()
    context.config_dir.mkdir(parents=True, exist_ok=True)
    search_policy_source = CORPUS_ROOT / "config" / "search_policy.json"
    (context.config_dir / "search_policy.json").write_text(
        search_policy_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (context.config_dir / "corpus_config.json").write_text(
        json.dumps(
            {
                "database": {"corpus_db": "./output/test.corpus.db"},
                "embeddings": {"dimensions": 1536, "batch_size": 50, "max_text_chars": 12000},
                "archive": {"enabled": True, "keep_archived": True},
                "fts": {"enabled": True, "tokenizer": "unicode61"},
                "source": {"page_images_dir": "", "persist_page_images_in_db": False},
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


def install_release_payload(context: ModuleContext, release_payload: dict[str, Any]) -> None:
    release_text = json.dumps(release_payload, indent=2, ensure_ascii=False)
    published_path = context.config_dir / "semantic_release.default.json"
    active_path = context.state_dir / "semantic_release.active.json"
    published_path.write_text(release_text, encoding="utf-8")
    active_path.write_text(release_text, encoding="utf-8")
    expected = BASELINE.normalize_phase0_release_payload(release_payload)
    if BASELINE.normalize_phase0_release_payload(json.loads(published_path.read_text(encoding="utf-8"))) != expected:
        raise AssertionError("Published release mirror drifted from the installed semantic release payload.")
    if BASELINE.normalize_phase0_release_payload(json.loads(active_path.read_text(encoding="utf-8"))) != expected:
        raise AssertionError("Active release mirror drifted from the installed semantic release payload.")
