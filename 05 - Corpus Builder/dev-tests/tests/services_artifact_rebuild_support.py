from __future__ import annotations

from pathlib import Path

from corpus_builder.context import ModuleContext
from corpus_builder.models import atomic_json_write
from tests.semantic_release_test_support import build_release_variant

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def write_default_config(context: ModuleContext) -> None:
    atomic_json_write(
        context.config_path,
        {
            "database": {"corpus_db": "./output/corpus.db"},
            "source": {"persist_page_images_in_db": True},
        },
    )


def write_active_release(context: ModuleContext) -> None:
    write_default_config(context)
    payload = build_release_variant(project_root=PROJECT_ROOT, projection_ids=["housing.default.v1"])
    atomic_json_write(context.state_dir / "semantic_release.active.json", payload)


def write_json_artifact(path: Path, payload: dict) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
