"""Success-only publication for finalized pipeline records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import storage_repository, success_publication
from .success_repository_steps import (
    extra_request_page_images,
    publish_named_outputs,
    publish_page_images,
    publish_raw_paths,
)
from .success_request_publication import publish_request_paths


def _extra_request_page_images(record: Any):
    return extra_request_page_images(record)


def publish_success_artifacts(engine: Any, record: Any, ctx: Any) -> str:
    route_root = storage_repository.route_artifact_root(ctx.ui_state, record.route_family)
    published_targets: list[Path] = []
    published_raw_paths = publish_raw_paths(engine, record, route_root, ctx.managed_roots, published_targets)
    if isinstance(published_raw_paths, str):
        return published_raw_paths
    published_page_assets = publish_page_images(engine, record, route_root, ctx.managed_roots, published_targets)
    if isinstance(published_page_assets, str):
        success_publication.cleanup_published_targets(engine, published_targets, ctx.managed_roots)
        return published_page_assets
    published_request_paths = publish_request_paths(
        engine,
        record,
        route_root,
        ctx.managed_roots,
        published_targets,
        published_page_assets.primary_paths,
        published_page_assets.asset_target_map,
    )
    if isinstance(published_request_paths, str):
        success_publication.cleanup_published_targets(engine, published_targets, ctx.managed_roots)
        return published_request_paths
    published_structured_paths = publish_named_outputs(
        engine,
        record,
        route_root,
        ctx.managed_roots,
        published_targets,
        attr_list="structured_paths",
        attr_single="structured_path",
        publication_name="structured",
        action="Structured publication",
        noun="Structured output",
    )
    if isinstance(published_structured_paths, str):
        success_publication.cleanup_published_targets(engine, published_targets, ctx.managed_roots)
        return published_structured_paths
    published_validation_paths = publish_named_outputs(
        engine,
        record,
        route_root,
        ctx.managed_roots,
        published_targets,
        attr_list="validation_report_paths",
        attr_single="validation_report_path",
        publication_name="validation",
        action="Validator publication",
        noun="Validator report",
    )
    if isinstance(published_validation_paths, str):
        success_publication.cleanup_published_targets(engine, published_targets, ctx.managed_roots)
        return published_validation_paths
    published_normalized_paths = publish_named_outputs(
        engine,
        record,
        route_root,
        ctx.managed_roots,
        published_targets,
        attr_list="normalized_paths",
        attr_single="normalized_path",
        publication_name="normalized",
        action="Normalizer publication",
        noun="Normalizer output",
    )
    if isinstance(published_normalized_paths, str):
        success_publication.cleanup_published_targets(engine, published_targets, ctx.managed_roots)
        return published_normalized_paths
    working_paths = success_publication.collect_working_paths(record)
    working_paths.extend(path for path in published_page_assets.extra_working_paths if path not in working_paths)
    record.artifacts.optimizer_raw_paths = [str(path) for path in published_raw_paths]
    record.artifacts.optimizer_page_image_paths = [str(path) for path in published_page_assets.primary_paths]
    record.artifacts.optimizer_ocr_request_paths = [str(path) for path in published_request_paths.optimizer_ocr_paths]
    record.artifacts.optimizer_ocr_request_path = str(published_request_paths.optimizer_ocr_paths[0]) if published_request_paths.optimizer_ocr_paths else ""
    record.artifacts.interpreter_request_paths = [str(path) for path in published_request_paths.interpreter_paths]
    record.artifacts.interpreter_request_path = str(published_request_paths.interpreter_paths[0]) if published_request_paths.interpreter_paths else ""
    record.artifacts.interpreter_debug_bundle_path = ""
    record.artifacts.structured_paths = [str(path) for path in published_structured_paths]
    record.artifacts.structured_path = str(published_structured_paths[0]) if published_structured_paths else ""
    record.artifacts.validation_report_paths = [str(path) for path in published_validation_paths]
    record.artifacts.validation_report_path = str(published_validation_paths[0]) if published_validation_paths else ""
    record.artifacts.normalized_paths = [str(path) for path in published_normalized_paths]
    record.artifacts.normalized_path = str(published_normalized_paths[0]) if published_normalized_paths else ""
    record.artifacts.normalizer_request_paths = [str(path) for path in published_request_paths.normalizer_paths]
    record.artifacts.normalizer_request_path = str(published_request_paths.normalizer_paths[0]) if published_request_paths.normalizer_paths else ""
    success_publication.cleanup_working_paths(engine, working_paths, ctx.managed_roots, keep_paths=published_targets)
    return ""
