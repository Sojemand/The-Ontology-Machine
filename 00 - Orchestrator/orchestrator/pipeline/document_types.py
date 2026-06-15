"""Named paths shared across document-stage workflow modules."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from . import path_budget, policy, storage_repository, validation
from .artifact_repository_files import atomic_copy_file

_PAGE_STAGE_PARENT_RE = re.compile(r"^.+\.p\d{3}\.of\d{3}$")


@dataclass(frozen=True)
class DocumentStagePaths:
    doc_runtime_dir: Path
    working_source_path: Path
    working_artifact_root: Path
    request_root: Path
    working_request_path: Path
    interpreter_debug_root: Path
    working_interpreter_debug_dir: Path
    structured_root: Path
    working_structured_path: Path
    validation_root: Path
    working_validation_path: Path
    normalized_root: Path
    working_normalized_path: Path
    working_log_path: Path
    published_route_root: Path
    corpus_db_path: Path
    optimizer_ocr_request_dir: Path | None = None

    def __post_init__(self) -> None:
        if self.optimizer_ocr_request_dir is None:
            object.__setattr__(self, "optimizer_ocr_request_dir", self.request_root / "_ocr")


def build_document_stage_paths(engine: Any, record: Any, ctx: Any) -> DocumentStagePaths:
    doc_runtime_dir = path_budget.runtime_doc_dir(ctx.runtime_dir, record.content_hash)
    source_root = doc_runtime_dir / "source"
    working_artifact_root = doc_runtime_dir / "artifacts"
    request_root = doc_runtime_dir / "requests"
    interpreter_debug_root = doc_runtime_dir / "interpreter_debug"
    structured_root = doc_runtime_dir / "structured"
    validation_root = doc_runtime_dir / "validation"
    normalized_root = doc_runtime_dir / "normalized"
    logs_root = doc_runtime_dir / "logs"
    source_name = policy.safe_file_name(Path(record.original_source_path or record.source_path or record.file_name).name)
    normalized_name = path_budget.budgeted_name(normalized_root, policy.normalized_output_path(engine, record).name)
    structured_name = normalized_name.replace(".structured.normalized.json", ".structured.json")
    validation_name = path_budget.budgeted_name(validation_root, policy.planned_validation_output_path(engine, record).name)
    log_name = path_budget.budgeted_name(logs_root, policy.log_output_path(engine, record).name)
    working_source_name = path_budget.budgeted_name(source_root, source_name)
    return DocumentStagePaths(
        doc_runtime_dir=doc_runtime_dir,
        working_source_path=source_root / working_source_name,
        working_artifact_root=working_artifact_root,
        request_root=request_root,
        working_request_path=request_root / policy.request_file_name(),
        optimizer_ocr_request_dir=request_root / "_ocr",
        interpreter_debug_root=interpreter_debug_root,
        working_interpreter_debug_dir=interpreter_debug_root,
        structured_root=structured_root,
        working_structured_path=structured_root / structured_name,
        validation_root=validation_root,
        working_validation_path=validation_root / validation_name,
        normalized_root=normalized_root,
        working_normalized_path=normalized_root / normalized_name,
        working_log_path=logs_root / log_name,
        published_route_root=storage_repository.route_artifact_root(ctx.ui_state, record.route_family),
        corpus_db_path=storage_repository.corpus_db_path(ctx.ui_state),
    )


def prepare_document_runtime(engine: Any, record: Any, paths: DocumentStagePaths, *, allowed_roots: tuple[Path, ...]) -> None:
    if paths.doc_runtime_dir.exists():
        shutil.rmtree(paths.doc_runtime_dir, ignore_errors=True)
    source_path = Path(record.source_path or record.original_source_path)
    if not validation.ensure_managed_path(engine, source_path, allowed_roots, action="Working source", noun="source path"):
        raise ValueError(f"Source path is outside the pipeline: {source_path}")
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"Source file is missing: {source_path}")
    paths.working_source_path.parent.mkdir(parents=True, exist_ok=True)
    paths.working_artifact_root.mkdir(parents=True, exist_ok=True)
    paths.working_request_path.parent.mkdir(parents=True, exist_ok=True)
    paths.optimizer_ocr_request_dir.mkdir(parents=True, exist_ok=True)
    paths.working_interpreter_debug_dir.mkdir(parents=True, exist_ok=True)
    paths.working_structured_path.parent.mkdir(parents=True, exist_ok=True)
    paths.working_validation_path.parent.mkdir(parents=True, exist_ok=True)
    paths.working_normalized_path.parent.mkdir(parents=True, exist_ok=True)
    paths.working_log_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_copy_file(source_path, paths.working_source_path)


def page_request_path(paths: DocumentStagePaths, raw_path: Path) -> Path:
    return _page_request_artifact_path(paths, raw_path, "interpreter_request")


def page_normalizer_request_path(paths: DocumentStagePaths, raw_path: Path) -> Path:
    return _page_request_artifact_path(paths, raw_path, "normalizer_request")


def _page_request_artifact_path(paths: DocumentStagePaths, raw_path: Path, request_key: str) -> Path:
    request_name = policy.request_file_name(request_key)
    slug = path_budget.budgeted_page_name(
        paths.request_root,
        _page_stage_slug(raw_path),
        reserved=len(request_name) + 1,
    )
    request_dir = paths.request_root / slug
    return request_dir / path_budget.budgeted_name(request_dir, request_name)


def page_structured_path(paths: DocumentStagePaths, raw_path: Path) -> Path:
    name = path_budget.budgeted_page_name(paths.structured_root, _page_stage_slug(raw_path), suffix=".structured.json")
    return paths.structured_root / name


def page_validation_path(paths: DocumentStagePaths, raw_path: Path, *, files_profile: bool) -> Path:
    suffix = ".files_validation_report.json" if files_profile else ".vision_validation_report.json"
    name = path_budget.budgeted_page_name(paths.validation_root, _page_stage_slug(raw_path), suffix=suffix)
    return paths.validation_root / name


def page_normalized_path(paths: DocumentStagePaths, raw_path: Path) -> Path:
    name = path_budget.budgeted_page_name(
        paths.normalized_root,
        _page_stage_slug(raw_path),
        suffix=".structured.normalized.json",
    )
    return paths.normalized_root / name


def page_interpreter_debug_dir(paths: DocumentStagePaths, raw_path: Path) -> Path:
    slug = path_budget.budgeted_page_name(paths.interpreter_debug_root, _page_stage_slug(raw_path))
    return paths.interpreter_debug_root / slug


def _page_stage_slug(raw_path: Path) -> str:
    if _is_page_request(raw_path):
        return raw_path.parent.name
    name = raw_path.name
    for suffix in (
        ".structured.normalized.json",
        ".structured.json",
        ".files_validation_report.json",
        ".vision_validation_report.json",
        ".raw.json",
        ".json",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return raw_path.stem


def _is_page_request(path: Path) -> bool:
    parent_name = str(path.parent.name or "").strip()
    if not _PAGE_STAGE_PARENT_RE.match(parent_name):
        return False
    lower_name = path.name.lower()
    request_names = {
        policy.request_file_name("ocr_request").lower(),
        policy.request_file_name("interpreter_request").lower(),
        policy.request_file_name("normalizer_request").lower(),
    }
    if lower_name in request_names:
        return True
    if not lower_name.endswith(".json"):
        return False
    for suffix in (
        ".structured.normalized.json",
        ".structured.json",
        ".files_validation_report.json",
        ".vision_validation_report.json",
        ".raw.json",
    ):
        if lower_name.endswith(suffix):
            return False
    return True
