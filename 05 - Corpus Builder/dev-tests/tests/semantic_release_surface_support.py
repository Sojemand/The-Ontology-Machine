from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.context import ModuleContext
from corpus_builder.semantic_release import build_release_fingerprint
from corpus_builder.services import build_load_bundle, load_batch
from .semantic_release_test_support import build_normalizer_release_bundle, build_release_variant

PROJECT_ROOT = Path(__file__).parent.parent.parent

def _make_context(tmp_path: Path) -> ModuleContext:
    context = ModuleContext(tmp_path)
    context.ensure_runtime_dirs()
    context.config_dir.mkdir(parents=True, exist_ok=True)
    release_source = PROJECT_ROOT / "config" / "semantic_release.default.json"
    search_policy_source = PROJECT_ROOT / "config" / "search_policy.json"
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

def _customized_release(release: dict[str, object]) -> dict[str, object]:
    release["release_id"] = "custom.release.v1"
    release["release_version"] = "custom.v1"
    release["master_taxonomy_id"] = "custom.taxonomy"
    release["master_taxonomy_version"] = "custom.v1"
    release["master_taxonomy_release_id"] = "custom.taxonomy.release"
    master = release.get("master_taxonomy")
    if isinstance(master, dict):
        master["taxonomy_id"] = "custom.taxonomy"
        master["taxonomy_version"] = "custom.v1"
    for payload in _embedded_release_headers(release):
        payload["release_id"] = release["release_id"]
        payload["release_version"] = release["release_version"]
        payload["master_taxonomy_release_id"] = release["master_taxonomy_release_id"]
        payload["runtime_locale"] = release.get("runtime_locale") or "en"
    _refresh_release_fingerprint(release)
    return release

def _embedded_release_headers(release: dict[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    projection_catalog = release.get("projection_catalog")
    if isinstance(projection_catalog, dict):
        result.append(projection_catalog)
    runtime_assets = release.get("runtime_semantic_assets")
    if isinstance(runtime_assets, dict):
        result.append(runtime_assets)
        runtime_projection_catalog = runtime_assets.get("projection_catalog")
        if isinstance(runtime_projection_catalog, dict):
            result.append(runtime_projection_catalog)
    return result

def _write_release_variant(
    context: ModuleContext,
    *,
    projection_ids: list[str] | None = None,
    master_taxonomy_release_id: str | None = None,
) -> Path:
    release = build_release_variant(
        project_root=PROJECT_ROOT,
        projection_ids=projection_ids,
        master_taxonomy_release_id=master_taxonomy_release_id,
    )
    variant_path = context.output_dir / "semantic_release.variant.json"
    variant_path.write_text(json.dumps(release, indent=2, ensure_ascii=False), encoding="utf-8")
    return variant_path

def _refresh_release_fingerprint(release: dict[str, object]) -> None:
    release["fingerprint"] = build_release_fingerprint(release)
    fingerprint = str(release["fingerprint"])
    release["release_fingerprint"] = fingerprint
    projection_catalog = release.get("projection_catalog")
    if isinstance(projection_catalog, dict):
        projection_catalog["release_fingerprint"] = fingerprint
    runtime_assets = release.get("runtime_semantic_assets")
    if isinstance(runtime_assets, dict):
        runtime_assets["release_fingerprint"] = fingerprint
        runtime_projection_catalog = runtime_assets.get("projection_catalog")
        if isinstance(runtime_projection_catalog, dict):
            runtime_projection_catalog["release_fingerprint"] = fingerprint
        vision_policy_bundle = runtime_assets.get("vision_policy_bundle")
        if isinstance(vision_policy_bundle, dict):
            vision_policy_bundle["release_fingerprint"] = fingerprint

def _load_normalized(context: ModuleContext, db_path: Path, payload: dict[str, object], stem: str) -> None:
    normalized_path = context.output_dir / f"{stem}.structured.normalized.json"
    normalized_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    load_batch(context, [build_load_bundle(context, normalized_path=normalized_path, corpus_db_path=db_path)])
