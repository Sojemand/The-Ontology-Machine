"""Error-case freezing for failed or cancelled pipeline records."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import utc_now_iso
from ..state import atomic_json_write
from . import artifact_repository, path_budget, policy, storage_repository, validation
from .bundle_repository_helpers import (
    artifact_values,
    budgeted_raw_target,
    copy_many,
    copy_named_many,
    copy_page_images,
    copy_single,
    extra_request_page_images,
)
from .bundle_publication import copy_requests_to_bundle, copy_run_log_snapshot


@dataclass(frozen=True)
class FrozenBundleArtifacts:
    source_path: str = ""
    optimizer_raw_paths: tuple[str, ...] = ()
    optimizer_page_image_paths: tuple[str, ...] = ()
    optimizer_ocr_request_paths: tuple[str, ...] = ()
    optimizer_ocr_request_path: str = ""
    interpreter_request_paths: tuple[str, ...] = ()
    interpreter_request_path: str = ""
    interpreter_debug_bundle_path: str = ""
    structured_paths: tuple[str, ...] = ()
    structured_path: str = ""
    validation_report_paths: tuple[str, ...] = ()
    validation_report_path: str = ""
    normalized_paths: tuple[str, ...] = ()
    normalized_path: str = ""
    normalizer_request_paths: tuple[str, ...] = ()
    normalizer_request_path: str = ""


def _extra_request_page_images(record: Any): return extra_request_page_images(record)

def bundle_dir(ui_state, record, *, stage: str = "", module_name: str = "") -> Path:
    root = storage_repository.error_case_route_root(ui_state, module_name or policy.error_stage_folder(stage), record.route_family)
    root.mkdir(parents=True, exist_ok=True)
    return root


def move_source_into_bundle(engine: Any, record: Any, bundle_path: Path, *, allowed_roots: tuple[Path, ...]) -> Path | None:
    source_path = Path(record.source_path or record.original_source_path)
    target_path = storage_repository.publication_root(bundle_path, "originals") / policy.record_relative_output_path(engine, record, purpose="Error-Original")
    if source_path.exists():
        if not validation.ensure_managed_path(engine, source_path, allowed_roots, action="Error-Original", noun="Source path"):
            return None
        return artifact_repository.move_file_with_conflict_handling(
            engine,
            source_path,
            target_path,
            action="error_bundle",
            content_hash=record.content_hash,
            allowed_roots=allowed_roots,
        )
    if target_path.exists() and artifact_repository.path_matches_hash(target_path, record.content_hash):
        return target_path
    return None


def freeze_bundle_artifacts(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    run_log_path: Path | None = None,
    source_path: Path | None = None,
    page_suffix: str = "",
) -> FrozenBundleArtifacts:
    raw_paths = tuple(
        str(path)
        for path in copy_many(
            engine,
            record.artifacts.optimizer_raw_paths,
            bundle_path,
            allowed_roots=allowed_roots,
            target_builder=lambda source, index: budgeted_raw_target(
                engine,
                record,
                bundle_path,
                source,
                index=index,
                page_suffix=page_suffix,
            ),
        )
    )
    page_assets = copy_page_images(engine, record, bundle_path, allowed_roots=allowed_roots)
    page_image_paths = tuple(str(path) for path in page_assets.primary_paths)
    request_artifacts = copy_requests_to_bundle(
        engine,
        record,
        bundle_path,
        allowed_roots=allowed_roots,
        source_path=source_path,
        page_image_paths=page_assets.primary_paths,
        page_target_map=page_assets.page_target_map,
        page_suffix=page_suffix,
    )
    debug_target = _debug_bundle_target(record, bundle_path, page_suffix=page_suffix)
    debug_bundle_path = copy_single(
        engine,
        record.artifacts.interpreter_debug_bundle_path,
        debug_target,
        allowed_roots=allowed_roots,
    )
    structured_paths = tuple(
        str(path)
        for path in copy_named_many(
            engine,
            artifact_values(record, "structured_paths", "structured_path"),
            storage_repository.publication_root(bundle_path, "structured") / policy.record_relative_output_path(engine, record, purpose="Structured-Output").parent,
            allowed_roots=allowed_roots,
        )
    )
    validation_paths = tuple(
        str(path)
        for path in copy_named_many(
            engine,
            artifact_values(record, "validation_report_paths", "validation_report_path"),
            storage_repository.publication_root(bundle_path, "validation") / policy.record_relative_output_path(engine, record, purpose="Validator-Report").parent,
            allowed_roots=allowed_roots,
        )
    )
    normalized_paths = tuple(
        str(path)
        for path in copy_named_many(
            engine,
            artifact_values(record, "normalized_paths", "normalized_path"),
            storage_repository.publication_root(bundle_path, "normalized") / policy.record_relative_output_path(engine, record, purpose="Normalizer-Output").parent,
            allowed_roots=allowed_roots,
        )
    )
    copy_run_log_snapshot(engine, record, bundle_path, allowed_roots=allowed_roots, run_log_path=run_log_path)
    return FrozenBundleArtifacts(
        source_path=str(source_path) if source_path is not None else "",
        optimizer_raw_paths=raw_paths,
        optimizer_page_image_paths=page_image_paths,
        optimizer_ocr_request_paths=tuple(str(path) for path in request_artifacts.optimizer_ocr_paths),
        optimizer_ocr_request_path=str(request_artifacts.optimizer_ocr_paths[0]) if request_artifacts.optimizer_ocr_paths else "",
        interpreter_request_paths=tuple(str(path) for path in request_artifacts.interpreter_paths),
        interpreter_request_path=str(request_artifacts.interpreter_paths[0]) if request_artifacts.interpreter_paths else "",
        interpreter_debug_bundle_path=str(debug_bundle_path) if debug_bundle_path is not None else "",
        structured_paths=structured_paths,
        structured_path=structured_paths[0] if structured_paths else "",
        validation_report_paths=validation_paths,
        validation_report_path=validation_paths[0] if validation_paths else "",
        normalized_paths=normalized_paths,
        normalized_path=normalized_paths[0] if normalized_paths else "",
        normalizer_request_paths=tuple(str(path) for path in request_artifacts.normalizer_paths),
        normalizer_request_path=str(request_artifacts.normalizer_paths[0]) if request_artifacts.normalizer_paths else "",
    )


def _debug_bundle_target(record: Any, bundle_path: Path, *, page_suffix: str) -> Path:
    source_name = Path(str(record.artifacts.interpreter_debug_bundle_path or "interpreter.debug.json")).name
    debug_root = bundle_path / "debug"
    if page_suffix:
        debug_root = debug_root / page_suffix.strip(".")
    return debug_root / path_budget.budgeted_name(debug_root, source_name)


def bundle_manifest_path(engine: Any, record: Any, bundle_path: Path) -> Path:
    relative_path = policy.error_manifest_output_path(engine, record)
    target_dir = storage_repository.publication_root(bundle_path, "logs") / relative_path.parent
    return target_dir / path_budget.budgeted_name(target_dir, relative_path.name)


def write_bundle_manifest(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    stage: str,
    reason: str,
    disposition: str,
    module_name: str,
) -> Path:
    payload = record.to_dict()
    payload.update(
        {
            "bundle_module": module_name,
            "bundle_stage": stage,
            "bundle_reason": reason,
            "bundle_disposition": disposition,
            "manifest_updated_at": utc_now_iso(),
        }
    )
    manifest_path = bundle_manifest_path(engine, record, bundle_path)
    atomic_json_write(manifest_path, payload)
    return manifest_path
