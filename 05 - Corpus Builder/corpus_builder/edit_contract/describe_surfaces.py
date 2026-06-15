"""Descriptor builders for Corpus Builder edit surfaces."""

from __future__ import annotations

from .operations import action_buttons
from .types import (
    EMBEDDINGS_POLICY_SURFACE_ID,
    SEARCH_POLICY_SURFACE_ID,
    SETTINGS_SURFACE_ID,
)

_SETTINGS_GROUPS = (
    ("Storage", ("database.corpus_db",)),
    ("Archive / FTS", ("archive.enabled", "archive.keep_archived", "fts.enabled", "fts.tokenizer")),
    (
        "Source / Semantic",
        (
            "source.page_images_dir",
            "source.persist_page_images_in_db",
            "semantic.published_release_path",
            "semantic.active_release_path",
            "semantic.release_report_path",
        ),
    ),
)
_EMBEDDINGS_GROUPS = (("Embeddings", ("embeddings.dimensions", "embeddings.batch_size", "embeddings.max_text_chars")),)
_SEARCH_GROUPS = (
    ("Fulltext", ("fulltext.limit_default",)),
    (
        "Semantic / Hybrid",
        (
            "semantic.top_k_default",
            "hybrid.top_k_default",
            "hybrid.candidate_multiplier",
            "hybrid.fts_weight",
            "hybrid.vec_weight",
        ),
    ),
    ("Readonly / FTS", ("readonly.max_rows", "fts.normalize_by_max_score")),
)


def describe_surfaces(*, module_root, settings: dict | None = None) -> list[dict]:
    return [
        _descriptor(
            SETTINGS_SURFACE_ID,
            label="Settings",
            kind="settings",
            storage_kind="json_file",
            source_path="config/corpus_config.json",
            editable=True,
            preview=["form", "json", "diff"],
            runtime_impact="next_module_operation",
            drift_status="explicit_file",
            section="Settings",
            field_groups=_groups(_SETTINGS_GROUPS),
            action_buttons=action_buttons(SETTINGS_SURFACE_ID, module_root=module_root, settings=settings),
        ),
        _descriptor(
            EMBEDDINGS_POLICY_SURFACE_ID,
            label="Embeddings Policy",
            kind="policy",
            storage_kind="json_file",
            source_path="config/corpus_config.json",
            editable=True,
            preview=["form", "json", "diff"],
            runtime_impact="next_generate_embeddings",
            drift_status="split_owner",
            section="Settings",
            field_groups=_groups(_EMBEDDINGS_GROUPS),
            action_buttons=action_buttons(EMBEDDINGS_POLICY_SURFACE_ID, module_root=module_root, settings=settings),
        ),
        _descriptor(
            SEARCH_POLICY_SURFACE_ID,
            label="Search Policy",
            kind="policy",
            storage_kind="json_file",
            source_path="config/search_policy.json",
            editable=True,
            preview=["form", "json", "diff"],
            runtime_impact="next_search",
            drift_status="explicit_file",
            section="Settings",
            field_groups=_groups(_SEARCH_GROUPS),
            action_buttons=action_buttons(SEARCH_POLICY_SURFACE_ID, module_root=module_root, settings=settings),
        ),
    ]


def _descriptor(
    surface_id: str,
    *,
    label: str,
    kind: str,
    storage_kind: str,
    source_path: str,
    editable: bool,
    preview: list[str],
    runtime_impact: str,
    drift_status: str,
    section: str,
    field_groups: list[dict[str, object]] | None = None,
    action_buttons: list[dict] | None = None,
) -> dict:
    descriptor = {
        "module_key": "corpus_builder",
        "surface_id": surface_id,
        "label": label,
        "kind": kind,
        "owner": "corpus_builder",
        "storage_kind": storage_kind,
        "source_path": source_path,
        "editable": editable,
        "validation": {"mode": "owner_contract", "fail_closed": editable},
        "preview": list(preview),
        "operation_links": [],
        "runtime_impact": runtime_impact,
        "drift_status": drift_status,
        "section": section,
        "render_actions_inline": False,
    }
    if field_groups:
        descriptor["field_groups"] = field_groups
    if action_buttons:
        descriptor["action_buttons"] = action_buttons
    return descriptor


def _groups(items: tuple[tuple[str, tuple[str, ...]], ...]) -> list[dict[str, object]]:
    return [{"label": label, "fields": list(fields)} for label, fields in items]
