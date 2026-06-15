"""Record discovery, hashing and retry collection for the pipeline."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..models import DocumentRecord
from . import debug, record_corpus_lookup, storage_repository, validation

_SUCCESS_DISPOSITIONS = {"success", "needs_review"}


def build_pending_queue(engine: Any, ui_state) -> list[DocumentRecord]:
    managed_roots = storage_repository.managed_roots(engine, ui_state)
    input_records = discover_input_records(engine, ui_state, managed_roots)
    retry_records = collect_retry_records(engine, managed_roots=managed_roots)
    by_hash = {record.content_hash: record for record in retry_records}
    for record in input_records:
        by_hash[record.content_hash] = record
    return sorted(by_hash.values(), key=lambda item: item.relative_path.lower())


def discover_input_records(engine: Any, ui_state, managed_roots: tuple[Path, ...]) -> list[DocumentRecord]:
    input_root = Path(ui_state.input_folder)
    artifact_root = storage_repository.artifact_root(ui_state)
    excluded_roots = [
        storage_repository.error_root(ui_state),
        storage_repository.corpus_root(ui_state),
        engine._state_dir,
    ]
    if not root_contains_input(artifact_root, input_root):
        excluded_roots.insert(0, artifact_root)
    seen_hashes: set[str] = set()
    discovered: list[DocumentRecord] = []
    for file_path in iter_input_files(input_root, excluded_roots):
        content_hash = compute_hash(file_path)
        if content_hash in seen_hashes:
            debug.append_log(engine, f"[SKIP] Duplicate in input: {file_path}")
            continue
        seen_hashes.add(content_hash)
        relative_path = file_path.relative_to(input_root).as_posix()
        record = engine._state.documents.get(content_hash)
        if record is None:
            record = DocumentRecord(
                content_hash=content_hash,
                file_name=file_path.name,
                relative_path=relative_path,
                original_source_path=str(file_path),
                source_path=str(file_path),
            )
            engine._state.documents[content_hash] = record
        else:
            record.file_name = file_path.name
            record.relative_path = relative_path
            record.original_source_path = str(file_path)
            record.source_path = str(file_path)
            record.current_location = "input"
        if record.final_disposition in _SUCCESS_DISPOSITIONS and not record_corpus_lookup.record_exists_in_selected_corpus(engine, record, ui_state):
            reset_record_for_reprocessing(engine, record, file_path, reason="not in selected DB")
        record.touch()
        if record.final_disposition == "error" and not bundle_still_exists(engine, record, managed_roots):
            reset_record_for_reprocessing(engine, record, file_path)
        if record.final_disposition in {"success", "needs_review", "error"}:
            continue
        discovered.append(record)
    storage_repository.save_state(engine)
    return sorted(discovered, key=lambda item: item.relative_path.lower())


def collect_retry_records(
    engine: Any,
    *,
    filter_hashes: set[str] | None = None,
    managed_roots: tuple[Path, ...] | None = None,
) -> list[DocumentRecord]:
    retryable: list[DocumentRecord] = []
    for content_hash, record in engine._state.documents.items():
        if filter_hashes is not None and content_hash not in filter_hashes:
            continue
        if record.status not in {"error", "processing"} or record.final_disposition:
            continue
        if record.failed_attempts >= engine._max_failed_attempts or not record.source_path:
            continue
        source_path = Path(record.source_path)
        if managed_roots is not None and not validation.ensure_managed_path(
            engine, source_path, managed_roots, action="Retry", noun="source path"
        ):
            continue
        if source_path.exists():
            retryable.append(record)
    return sorted(retryable, key=lambda item: item.relative_path.lower())


def bundle_still_exists(engine: Any, record: DocumentRecord, managed_roots: tuple[Path, ...]) -> bool:
    if record.artifacts.bundle_manifest_path:
        manifest_path = Path(record.artifacts.bundle_manifest_path)
        if validation.ensure_managed_path(engine, manifest_path, managed_roots, action="Error case check", noun="manifest path"):
            return manifest_path.exists()
    if not record.artifacts.bundle_dir:
        return False
    bundle_path = Path(record.artifacts.bundle_dir)
    if not validation.ensure_managed_path(engine, bundle_path, managed_roots, action="Error case check", noun="error-case path"):
        return False
    return bundle_path.exists()


def reset_record_for_reprocessing(engine: Any, record: DocumentRecord, source_path: Path, *, reason: str = "") -> None:
    detail = f" ({reason})" if reason else ""
    debug.append_log(engine, f"[RESET] {record.relative_path}: file back in input - will be processed again{detail}")
    record.status = "pending"
    record.final_disposition = ""
    record.current_location = "input"
    record.source_path = str(source_path)
    record.attempts = 0
    record.failed_attempts = 0
    record.normalizer_failed_attempts = 0
    record.last_stage = ""
    record.last_error = ""
    record.review_reason = ""
    record.interpreter_needs_review = False
    record.interpreter_review_reason = ""
    record.validator_needs_review = False
    record.validator_review_reason = ""
    record.normalizer_needs_review = False
    record.normalizer_review_reason = ""
    record.route_family = ""
    record.optimizer_profile = ""
    record.interpreter_profile = ""
    record.optimizer_module_key = ""
    record.interpreter_module_key = ""
    record.intake_reason = ""
    record.artifacts.optimizer_raw_paths = []
    record.artifacts.optimizer_page_image_paths = []
    record.artifacts.optimizer_ocr_request_paths = []
    record.artifacts.optimizer_ocr_request_path = ""
    record.artifacts.bundle_dir = ""
    record.artifacts.bundle_manifest_path = ""
    record.artifacts.interpreter_request_paths = []
    record.artifacts.interpreter_request_path = ""
    record.artifacts.interpreter_debug_bundle_path = ""
    record.artifacts.structured_paths = []
    record.artifacts.structured_path = ""
    record.artifacts.normalized_paths = []
    record.artifacts.normalized_path = ""
    record.artifacts.normalizer_request_paths = []
    record.artifacts.normalizer_request_path = ""
    record.artifacts.validation_report_paths = []
    record.artifacts.validation_report_path = ""
    record.touch()


def compute_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def iter_input_files(input_root: Path, excluded_roots: list[Path]) -> list[Path]:
    resolved_excluded = [validation.resolved_path(root) for root in excluded_roots]
    files: list[Path] = []
    for candidate in sorted(input_root.rglob("*")):
        if not candidate.is_file():
            continue
        resolved = validation.resolved_path(candidate)
        if any(validation.is_within(resolved, root) for root in resolved_excluded if root.exists()):
            continue
        files.append(candidate)
    return files


def root_contains_input(root: Path, input_root: Path) -> bool:
    resolved_input = validation.resolved_path(input_root)
    resolved_root = validation.resolved_path(root)
    return resolved_root == resolved_input or validation.is_within(resolved_input, resolved_root)
