"""Helpers for optimizer stage output targeting and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import path_budget, policy, validation


def requested_raw_output_path(engine: Any, record: Any, paths: Any) -> Path:
    runtime_raw_root = paths.working_artifact_root / "raw_extracts"
    return runtime_raw_root / path_budget.budgeted_name(runtime_raw_root, policy.raw_output_path(engine, record).name)


def requested_page_assets_dir(engine: Any, record: Any, paths: Any) -> Path:
    runtime_page_root = paths.working_artifact_root / "page_assets"
    page_dir_name = path_budget.budgeted_name(
        runtime_page_root,
        f"{policy.record_relative_output_path(engine, record, purpose='Page-Assets').name}.{path_budget.hash8(record.content_hash)}",
        reserved=32,
    )
    return runtime_page_root / page_dir_name


def requested_ocr_request_dir(paths: Any) -> Path:
    return paths.optimizer_ocr_request_dir


def logical_source_path(engine: Any, record: Any) -> str:
    return policy.record_relative_output_path(engine, record, purpose="Optimizer-Input").as_posix()


def validated_direct_raw_output(
    engine: Any,
    raw_path_text: str,
    *,
    raw_dest: Path,
    allowed_roots: tuple[Path, ...],
    display_name: str,
) -> tuple[Path | None, str]:
    raw_path, raw_error = validation.validated_existing_file_path(
        engine,
        raw_path_text,
        allowed_roots=allowed_roots,
        action="Raw-Output",
        noun=f"{display_name} output",
        missing_message=f"{display_name} did not provide raw output.",
    )
    if raw_error:
        return None, raw_error
    if validation.resolved_path(raw_path) != validation.resolved_path(raw_dest):
        return None, f"{display_name} output differs from the requested raw target: {raw_path}"
    return raw_path, ""


def validated_direct_raw_outputs(
    engine: Any,
    raw_path_texts: list[str],
    *,
    raw_dest: Path,
    allowed_roots: tuple[Path, ...],
    display_name: str,
) -> tuple[list[Path], str]:
    validated: list[Path] = []
    seen: set[Path] = set()
    for raw_path_text in raw_path_texts:
        raw_path, raw_error = validation.validated_existing_file_path(
            engine,
            raw_path_text,
            allowed_roots=allowed_roots,
            action="Raw-Output",
        noun=f"{display_name} output",
            missing_message=f"{display_name} did not provide raw output.",
        )
        if raw_error:
            return [], raw_error
        if raw_path in seen:
            continue
        seen.add(raw_path)
        validated.append(raw_path)
    if not validated:
        return [], f"{display_name} did not provide raw outputs."
    return validated, ""


def validated_direct_page_images(
    engine: Any,
    page_path_texts: list[str],
    *,
    page_dir: Path,
    allowed_roots: tuple[Path, ...],
    display_name: str,
) -> tuple[list[Path], str]:
    page_dir_resolved = validation.resolved_path(page_dir)
    page_paths: list[Path] = []
    for page_path_text in page_path_texts:
        page_path, page_error = validation.validated_existing_file_path(
            engine,
            page_path_text,
            allowed_roots=allowed_roots,
            action="Page-Image",
            noun=f"{display_name} page image",
            missing_message=f"{display_name} did not provide page images.",
        )
        if page_error:
            return [], page_error
        if validation.resolved_path(page_path.parent) != page_dir_resolved:
            return [], f"{display_name} page image differs from the requested target folder: {page_path}"
        page_paths.append(page_path)
    return page_paths, ""
