"""Orchestrator-owned request enrichment and request artifact publishing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import validation
from .request_enrichment_file import (
    build_file_request,
    normalized_interpreter_profile,
    select_page_targets,
)
from .request_enrichment_helpers import optional_mapping
from .request_enrichment_io import load_json_object, raw_stem, write_request_json
from .request_enrichment_paths import rewrite_request_paths
from .request_enrichment_projection import required_projection_catalog
from .request_enrichment_vision import build_vision_request

REQUEST_ENRICHMENT_STAGE_NAME = "Request Enrichment"
_REQUEST_FILE_NAME = "interpreter.request.json"


def build_working_request(
    modules: Any,
    *,
    interpreter_profile: str = "",
    module_key: str | None = None,
    raw_path: Path,
    request_path: Path,
    working_source_path: Path,
    working_page_paths: tuple[Path, ...],
    projection_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del modules, module_key
    payload = load_json_object(raw_path, error_prefix="Optimizer-Raw")
    request = _build_request(
        interpreter_profile,
        payload,
        working_page_paths=working_page_paths,
    )
    request["projection_catalog"] = required_projection_catalog(projection_catalog)
    page_targets = select_page_targets(payload, request, working_page_paths)
    request = rewrite_request_paths(
        request,
        request_parent=request_path.parent,
        source_target=working_source_path,
        page_targets=page_targets,
        page_target_map=_build_request_page_target_map(payload, request, page_targets),
        rewrite_source_file_path=True,
    )
    request_path.parent.mkdir(parents=True, exist_ok=True)
    write_request_json(request_path, request)
    return request


def build_working_requests(
    modules: Any,
    *,
    interpreter_profile: str = "",
    module_key: str | None = None,
    raw_path: Path,
    request_root: Path,
    working_source_path: Path,
    working_page_paths: tuple[Path, ...],
    projection_catalog: dict[str, Any] | None = None,
) -> list[Path]:
    del module_key
    request_path = request_root / raw_stem(raw_path) / _REQUEST_FILE_NAME
    build_working_request(
        modules,
        interpreter_profile=interpreter_profile,
        raw_path=raw_path,
        request_path=request_path,
        working_source_path=working_source_path,
        working_page_paths=working_page_paths,
        projection_catalog=projection_catalog,
    )
    return [request_path]


def publish_request_copy(
    engine: Any,
    source_request_path: Path,
    target_request_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    action: str,
    noun: str,
    source_target: Path | None,
    page_targets: tuple[Path, ...],
    page_target_map: dict[Path, Path] | None = None,
    rewrite_source_file_path: bool = True,
) -> str:
    if not str(source_request_path).strip() or str(source_request_path) in {".", ""}:
        return f"{noun} is missing."
    if not validation.ensure_managed_path(engine, source_request_path, allowed_roots, action=action, noun=noun):
        return f"{noun} is outside the pipeline: {source_request_path}"
    if not source_request_path.exists() or not source_request_path.is_file():
        return f"{noun} is missing: {source_request_path}"
    rewrite_page_asset_paths = bool(page_targets or page_target_map)
    request = rewrite_request_paths(
        load_json_object(source_request_path, error_prefix=noun),
        request_parent=target_request_path.parent,
        source_target=source_target,
        page_targets=page_targets,
        page_target_map=page_target_map,
        source_request_parent=source_request_path.parent,
        rewrite_source_file_path=rewrite_source_file_path,
        rewrite_page_asset_paths=rewrite_page_asset_paths,
    )
    if not rewrite_page_asset_paths:
        _strip_unpublished_page_asset_paths(request)
    try:
        target_request_path.parent.mkdir(parents=True, exist_ok=True)
        write_request_json(target_request_path, request)
    except Exception as exc:
        return f"{noun} could not be written: {exc}"
    return ""


def _build_request(
    interpreter_profile: str,
    payload: dict[str, Any],
    *,
    working_page_paths: tuple[Path, ...],
) -> dict[str, Any]:
    profile = normalized_interpreter_profile(interpreter_profile, payload)
    request = (
        build_file_request(payload, working_page_paths=working_page_paths)
        if profile == "file"
        else build_vision_request(payload, working_page_paths=working_page_paths)
    )
    context = optional_mapping(request.get("context"))
    context.setdefault("interpreter_profile", profile)
    request["context"] = context
    return request


def _strip_unpublished_page_asset_paths(request: dict[str, Any]) -> None:
    page_assets = request.get("page_assets")
    if not isinstance(page_assets, list):
        return
    for item in page_assets:
        if isinstance(item, dict):
            item.pop("path", None)


def _build_request_page_target_map(
    payload: dict[str, Any],
    request: dict[str, Any],
    page_targets: tuple[Path, ...],
) -> dict[Path, Path] | None:
    del payload, request, page_targets
    return None
