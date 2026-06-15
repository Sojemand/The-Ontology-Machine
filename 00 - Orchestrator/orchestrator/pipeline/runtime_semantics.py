"""Run-scoped runtime semantics resolution and cache helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..integrations.runtime_semantic_assets import build_runtime_semantic_assets, read_active_semantic_release
from ..state import atomic_json_write
from . import debug, storage_repository

RUNTIME_SEMANTICS_STAGE_NAME = "Runtime Semantics"
_RUNTIME_SEMANTIC_ASSETS_FILE_NAME = "runtime_semantic_assets.json"
_OPTIMIZER_RUNTIME_POLICY_FILE_NAME = "optimizer_runtime_semantic_assets.json"
_OPTIMIZER_INTERPRETER_PAGE_ASSET_DPI = 150


@dataclass(slots=True)
class RuntimeSemanticsState:
    cache_path: Path
    runtime_policy_path: Path
    release: dict[str, Any]
    runtime_semantic_assets: dict[str, Any]
    projection_catalog: dict[str, Any]
    resolved_corpus_db_path: str
    active_snapshot_id: str
    master_taxonomy_release_id: str
    runtime_locale: str
    release_id: str
    release_version: str
    release_fingerprint: str
    stage_detail: str


def ensure_initialized(engine: Any, ctx: Any) -> RuntimeSemanticsState:
    resolved_corpus_db_path = storage_repository.corpus_db_path(ctx.ui_state)
    debug.set_stage(engine, RUNTIME_SEMANTICS_STAGE_NAME, "Processing...", _starting_detail(ctx))
    debug.emit_snapshot(engine)
    release_path = ""
    try:
        release_detail = read_active_semantic_release(
            engine._modules,
            corpus_db_path=resolved_corpus_db_path,
        )
        release_path = str(release_detail.get("release_path") or "").strip()
        active_snapshot = release_detail.get("active_snapshot") if isinstance(release_detail.get("active_snapshot"), dict) else None
        active_snapshot_id = str((active_snapshot or {}).get("snapshot_id") or "").strip()
        resolved_db_key = str(resolved_corpus_db_path)
        state = getattr(ctx, "runtime_semantics", None)
        if (
            isinstance(state, RuntimeSemanticsState)
            and state.resolved_corpus_db_path == resolved_db_key
            and active_snapshot_id
            and state.active_snapshot_id == active_snapshot_id
        ):
            return state
        if active_snapshot is not None:
            runtime_assets = dict(active_snapshot["runtime_semantic_assets"])
            projection_catalog = dict(active_snapshot["projection_catalog"])
        else:
            runtime_assets = build_runtime_semantic_assets(engine._modules, release=release_detail["release"])
            projection_catalog = dict(runtime_assets["projection_catalog"])
        cache_path = ctx.runtime_dir / "runtime" / _RUNTIME_SEMANTIC_ASSETS_FILE_NAME
        optimizer_runtime_policy_path = ctx.runtime_dir / "runtime" / _OPTIMIZER_RUNTIME_POLICY_FILE_NAME
        atomic_json_write(cache_path, runtime_assets)
        atomic_json_write(optimizer_runtime_policy_path, _optimizer_runtime_policy_assets(runtime_assets))
        stage_detail = _stage_detail(
            release_id=str(release_detail["release_id"]),
            release_version=str(release_detail["release_version"]),
            release_fingerprint=str(release_detail["fingerprint"]),
            active_snapshot_id=active_snapshot_id,
        )
        state = RuntimeSemanticsState(
            cache_path=cache_path,
            runtime_policy_path=optimizer_runtime_policy_path,
            release=deepcopy(release_detail["release"]),
            runtime_semantic_assets=runtime_assets,
            projection_catalog=projection_catalog,
            resolved_corpus_db_path=resolved_db_key,
            active_snapshot_id=active_snapshot_id,
            master_taxonomy_release_id=str(
                release_detail.get("master_taxonomy_release_id")
                or (active_snapshot or {}).get("master_taxonomy_release_id")
                or ""
            ),
            runtime_locale=str(
                release_detail.get("runtime_locale")
                or (active_snapshot or {}).get("runtime_locale")
                or ""
            ),
            release_id=str(release_detail["release_id"]),
            release_version=str(release_detail["release_version"]),
            release_fingerprint=str(release_detail["fingerprint"]),
            stage_detail=stage_detail,
        )
        ctx.runtime_semantics = state
    except Exception as exc:
        detail = str(exc) or "Runtime Semantics could not be initialized."
        if release_path:
            detail = f"{detail} [release_path={release_path}]"
        debug.set_stage(engine, RUNTIME_SEMANTICS_STAGE_NAME, "Error", detail)
        debug.append_log(engine, f"[SEMANTICS-ERROR] {detail}")
        debug.emit_snapshot(engine)
        raise RuntimeError(detail) from exc
    debug.set_stage(engine, RUNTIME_SEMANTICS_STAGE_NAME, "Done", state.stage_detail)
    debug.append_log(engine, f"[SEMANTICS] {state.stage_detail}")
    debug.emit_snapshot(engine)
    return state


def restore_stage(engine: Any, ctx: Any) -> None:
    state = getattr(ctx, "runtime_semantics", None)
    if not isinstance(state, RuntimeSemanticsState):
        return
    debug.set_stage(engine, RUNTIME_SEMANTICS_STAGE_NAME, "Done", state.stage_detail)


def _optimizer_runtime_policy_assets(runtime_assets: dict[str, Any]) -> dict[str, Any]:
    assets = deepcopy(runtime_assets)
    bundle = assets.get("vision_policy_bundle")
    if isinstance(bundle, dict):
        bundle.pop("semantic_extraction_policy", None)
        ocr_policy = bundle.get("ocr_policy")
        if isinstance(ocr_policy, dict):
            ocr_policy.pop("projection_overrides", None)
            _force_optimizer_page_asset_dpi(ocr_policy)
    return assets


def _force_optimizer_page_asset_dpi(ocr_policy: dict[str, Any]) -> None:
    defaults = ocr_policy.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
        ocr_policy["defaults"] = defaults
    render = defaults.get("render")
    if not isinstance(render, dict):
        render = {}
        defaults["render"] = render
    render["page_image_dpi"] = _OPTIMIZER_INTERPRETER_PAGE_ASSET_DPI


def _starting_detail(ctx: Any) -> str:
    return "Resolving active release"


def _stage_detail(*, release_id: str, release_version: str, release_fingerprint: str, active_snapshot_id: str) -> str:
    fingerprint = release_fingerprint[:16]
    snapshot = active_snapshot_id[:16]
    parts = [part for part in (release_id, release_version, fingerprint, snapshot) if part]
    return " | ".join(parts) or "Runtime Semantics ready"
