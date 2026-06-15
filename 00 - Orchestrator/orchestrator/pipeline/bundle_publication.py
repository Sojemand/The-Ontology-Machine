"""Helpers for publishing bundle logs and rewritten request artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import artifact_repository, path_budget, policy, request_enrichment, storage_repository
from .bundle_request_artifacts import CopiedRequestArtifacts, MULTI_PAGE_REQUEST_RESERVED, copy_plain_requests_to_bundle


def copy_run_log_snapshot(
    engine: Any,
    record: Any,
    target_root: Path,
    *,
    allowed_roots: tuple[Path, ...],
    run_log_path: Path | None,
) -> None:
    if run_log_path is None:
        return
    relative_path = policy.log_output_path(engine, record)
    target_dir = storage_repository.publication_root(target_root, "logs") / relative_path.parent
    target = target_dir / path_budget.budgeted_name(target_dir, relative_path.name)
    artifact_repository.copy_if_exists(engine, run_log_path, target, allowed_roots=allowed_roots)


def copy_requests_to_bundle(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    source_path: Path | None,
    page_image_paths: tuple[Path, ...],
    page_target_map: dict[Path, Path] | None = None,
    page_suffix: str = "",
) -> CopiedRequestArtifacts:
    return CopiedRequestArtifacts(
        optimizer_ocr_paths=tuple(
            copy_plain_requests_to_bundle(
                engine,
                record,
                bundle_path,
                allowed_roots=allowed_roots,
                attr_list="optimizer_ocr_request_paths",
                attr_single="optimizer_ocr_request_path",
                request_key="ocr_request",
                purpose="OCR-Request",
                page_suffix=page_suffix,
            )
        ),
        interpreter_paths=tuple(
            _copy_interpreter_requests_to_bundle(
                engine,
                record,
                bundle_path,
                allowed_roots=allowed_roots,
                source_path=source_path,
                page_image_paths=page_image_paths,
                page_target_map=page_target_map,
                page_suffix=page_suffix,
            )
        ),
        normalizer_paths=tuple(
            copy_plain_requests_to_bundle(
                engine,
                record,
                bundle_path,
                allowed_roots=allowed_roots,
                attr_list="normalizer_request_paths",
                attr_single="normalizer_request_path",
                request_key="normalizer_request",
                purpose="Normalizer-Request",
                page_suffix=page_suffix,
            )
        ),
    )


def _copy_interpreter_requests_to_bundle(
    engine: Any,
    record: Any,
    bundle_path: Path,
    *,
    allowed_roots: tuple[Path, ...],
    source_path: Path | None,
    page_image_paths: tuple[Path, ...],
    page_target_map: dict[Path, Path] | None = None,
    page_suffix: str = "",
) -> list[Path]:
    request_paths = list(getattr(record.artifacts, "interpreter_request_paths", []) or [])
    if not request_paths:
        request_source_text = str(record.artifacts.interpreter_request_path or "").strip()
        request_paths = [request_source_text] if request_source_text else []
    published: list[Path] = []
    single_request = len([path for path in request_paths if str(path).strip()]) == 1
    for request_source_text in request_paths:
        if not str(request_source_text).strip():
            continue
        source = Path(request_source_text)
        publication_root = storage_repository.publication_root(bundle_path, "requests")
        relative_output_path = policy.record_relative_output_path(
            engine,
            record,
            purpose="Interpreter-Request",
        )
        if single_request and page_suffix:
            relative_output_path = relative_output_path.with_name(f"{relative_output_path.name}{page_suffix}")
        request_root = publication_root / path_budget.budgeted_relative_path(
            publication_root,
            relative_output_path,
            reserved=MULTI_PAGE_REQUEST_RESERVED if not single_request else 0,
        )
        if single_request:
            target = request_root / policy.request_file_name()
        else:
            request_dir = request_root / path_budget.budgeted_page_name(
                request_root,
                source.parent.name,
                reserved=len(policy.request_file_name()) + 1,
            )
            target = request_dir / policy.request_file_name()
        error = request_enrichment.publish_request_copy(
            engine,
            source,
            target,
            allowed_roots=allowed_roots,
            action="Request-Bundle",
            noun="Interpreter-Request",
            source_target=source_path,
            page_targets=page_image_paths,
            page_target_map=page_target_map,
        )
        if error:
            from . import debug

            debug.append_log(engine, f"[ERROR] Request bundle failed: {error}")
            return published
        if target.exists():
            published.append(target)
    return published
