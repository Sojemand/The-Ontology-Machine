"""Summary-card builders for the Corpus Builder edit contract."""
from __future__ import annotations

import json
from pathlib import Path

from . import config_repository, repository


def build_summary_cards(
    *,
    module_root,
    settings: dict[str, object] | None = None,
    embeddings: dict[str, object] | None = None,
    search: dict[str, object] | None = None,
    capabilities: dict[str, object] | None = None,
) -> list[dict]:
    module_root = Path(module_root).resolve()
    if settings is None or embeddings is None:
        surfaces = config_repository.read_config_surfaces(module_root)
        settings = settings if settings is not None else surfaces["settings"]
        embeddings = embeddings if embeddings is not None else surfaces["embeddings"]
    search = search if search is not None else repository.read_search_policy(module_root)
    capabilities = capabilities if capabilities is not None else repository.read_debug_capabilities(module_root)
    published_path = _resolve_module_path(module_root, settings["semantic.published_release_path"])
    active_path = _resolve_module_path(module_root, settings["semantic.active_release_path"])
    report_path = _resolve_module_path(module_root, settings["semantic.release_report_path"])
    published_release = _load_json_dict(published_path)
    active_release = _load_json_dict(active_path)
    report = _load_json_dict(report_path)
    return [
        {
            "card_id": "module_role",
            "label": "Module Role",
            "body": "What this slot edits before later corpus, search, and semantic actions run.",
            "lines": [
                f"Corpus DB: {settings['database.corpus_db']}",
                "Owner Files: corpus_config.json, search_policy.json",
                f"Archive + FTS: {settings['archive.enabled']} / {settings['fts.enabled']}",
                f"FTS Tokenizer: {settings['fts.tokenizer']}",
                f"Page Images In DB: {settings['source.persist_page_images_in_db']}",
            ],
        },
        {
            "card_id": "release_state",
            "label": "Release State",
            "body": "Read-only view of the configured published bundle plus active and report files.",
            "lines": [
                f"Published Release: {_release_label(published_release)}",
                f"Published Path: {_path_status(settings['semantic.published_release_path'], published_path)}",
                f"Active Release: {_release_label(active_release)}",
                f"Pending Change: {_pending_change_label(published_release, active_release)}",
                f"Latest Report: {_report_label(report)}",
            ],
        },
        {
            "card_id": "search_embeddings_readiness",
            "label": "Search & Embeddings Readiness",
            "body": "Saved defaults that shape later embedding generation and search actions.",
            "lines": [
                f"Embedding Dimensions: {embeddings['embeddings.dimensions']}",
                f"Embedding Batch/Text Limit: {embeddings['embeddings.batch_size']} / {embeddings['embeddings.max_text_chars']}",
                f"Search Defaults: FTS {search['fulltext.limit_default']}, Semantic {search['semantic.top_k_default']}, Hybrid {search['hybrid.top_k_default']}",
                f"Hybrid Weights: {search['hybrid.fts_weight']} FTS / {search['hybrid.vec_weight']} Vec",
                f"Read-only Max Rows: {search['readonly.max_rows']}",
            ],
        },
        {
            "card_id": "capabilities_boundaries",
            "label": "Capabilities & Boundaries",
            "body": "What belongs in this slot and what still lives outside the slot.",
            "lines": [
                f"Contract Module: {capabilities.get('contract_module') or ''}",
                "Suite Actions: stage/activate, search, stats, export, rebuild",
                "Debug Host Only: scan_debug_input, debug_run",
                "Other Capabilities: load_document, healthcheck",
                "Embedding Model + state files: runtime-owned / read-only",
            ],
        },
    ]


def _resolve_module_path(module_root: Path, configured_path: str) -> Path:
    path = Path(str(configured_path).strip()).expanduser()
    return path if path.is_absolute() else (module_root / path)


def _load_json_dict(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _release_label(payload: dict[str, object] | None) -> str:
    if not payload:
        return "missing"
    release_id = str(payload.get("release_id") or "").strip()
    release_version = str(payload.get("release_version") or "").strip()
    projection_count = len(payload.get("projection_ids") or [])
    if release_id and release_version:
        return f"{release_id} @ {release_version} ({projection_count} projections)"
    if release_id:
        return release_id
    return "present"


def _path_status(configured_path: str, resolved_path: Path) -> str:
    status = "present" if resolved_path.exists() else "missing"
    return f"{configured_path} ({status})"


def _pending_change_label(
    published_release: dict[str, object] | None,
    active_release: dict[str, object] | None,
) -> str:
    if not published_release:
        return "unknown"
    if not active_release:
        return "yes"
    published_fingerprint = str(published_release.get("fingerprint") or "").strip()
    active_fingerprint = str(active_release.get("fingerprint") or "").strip()
    if published_fingerprint and active_fingerprint:
        return "no" if published_fingerprint == active_fingerprint else "yes"
    return "unknown"


def _report_label(payload: dict[str, object] | None) -> str:
    if not payload:
        return "missing"
    issues = payload.get("issues") or []
    warnings = payload.get("warnings") or []
    issue_count = len(issues) if isinstance(issues, list) else "?"
    warning_count = len(warnings) if isinstance(warnings, list) else "?"
    generated_at = str(payload.get("generated_at") or "").strip()
    if generated_at:
        return f"{issue_count} issues, {warning_count} warnings @ {generated_at}"
    return f"{issue_count} issues, {warning_count} warnings"
