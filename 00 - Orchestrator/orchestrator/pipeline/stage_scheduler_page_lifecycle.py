"""Page lifecycle helpers for the orchestrator stage scheduler."""

from __future__ import annotations

from typing import Any

from ..integrations import stage_name_for_module
from . import (
    corpus_workflow,
    debug,
    document_workflow,
    error_workflow,
    page_error_workflow,
    policy,
    storage_repository,
)
from .page_stage_types import PageStageResult, PageWorkItem
from .stage_scheduler_page_helpers import attach_failure_path, failed_pages_review_reason, record_debug_path
from .stage_scheduler_success_handlers import RunStageSchedulerSuccessHandlers


class RunStageSchedulerPageLifecycle(RunStageSchedulerSuccessHandlers):
    def _handle_page_failure(
        self,
        page: PageWorkItem,
        result: PageStageResult,
        *,
        stage_key: str,
        stage_name: str,
    ) -> None:
        attach_failure_path(page, stage_key, result.path)
        if stage_key == "normalizer" and result.request_path is not None:
            page.normalizer_request_path = result.request_path
        reason = result.reason or f"{stage_name} failed."
        if stage_key == "interpreter":
            page.interpreter_debug_bundle_path = record_debug_path(page.record)
        page.failed_attempts += 1
        page.last_stage = stage_name
        page.last_error = reason
        page.record.failed_attempts += 1
        page.record.last_stage = stage_name
        page.record.last_error = f"{page.label}: {reason}"
        page.record.touch()
        storage_repository.save_state(self._engine)
        debug.append_log(
            self._engine,
            f"[PAGE-ERROR] {page.record.relative_path}: {page.label} | {stage_name} | attempt {page.failed_attempts} -> {reason}",
        )
        if page.failed_attempts >= self._engine._max_failed_attempts:
            final_reason = f"{reason} (max {self._engine._max_failed_attempts} page errors reached)"
            page_error_workflow.route_page_to_error(self._engine, page, self._ctx, stage=stage_name, reason=final_reason)
            page.terminal = True
            page.succeeded = False
            state = self._document_runs.get(page.record.content_hash)
            if state is not None and page not in state.failed_pages:
                state.failed_pages.append(page)
            self._sync_record_artifacts(page.record.content_hash)
            self._finalize_document_if_complete(page.record.content_hash)
            return
        self._engine._snapshot.retries += 1
        retry_stage = result.retry_from or stage_key
        self._clear_page_outputs_for_retry(page, retry_stage)
        self._sync_record_artifacts(page.record.content_hash)
        debug.set_stage(
            self._engine,
            stage_name,
            "Retry",
            f"{page.label} | attempt {page.failed_attempts + 1}/{self._engine._max_failed_attempts}",
            progress_current=page.page_index,
            progress_total=page.page_total,
            progress_label="Pages",
        )
        debug.emit_snapshot(self._engine)
        self._enqueue_page_retry(page, retry_stage)

    def _clear_page_outputs_for_retry(self, page: PageWorkItem, retry_stage: str) -> None:
        if retry_stage in {"request"}:
            page.request_path = None
        if retry_stage in {"request", "interpreter"}:
            page.structured_path = None
            page.validation_path = None
            page.normalizer_request_path = None
            page.normalized_path = None
        elif retry_stage == "validator":
            page.validation_path = None
            page.normalizer_request_path = None
            page.normalized_path = None
        elif retry_stage == "normalizer":
            page.normalizer_request_path = None
            page.normalized_path = None

    def _enqueue_page_retry(self, page: PageWorkItem, retry_stage: str) -> None:
        inbox = {
            "request": self._request,
            "interpreter": self._interpreter,
            "validator": self._validator,
            "normalizer": self._normalizer,
            "corpus": self._corpus,
        }.get(retry_stage)
        if inbox is None:
            inbox = self._request
        inbox.send(page, front=True)

    def _finalize_document_if_complete(self, content_hash: str) -> None:
        state = self._document_runs.get(content_hash)
        if state is None or state.finalized or state.terminal_count < len(state.pages):
            return
        state.finalized = True
        active = state.active
        record = active.record
        if state.succeeded_pages:
            self._sync_record_artifacts(content_hash, successful_only=True)
            if state.failed_pages:
                reason = failed_pages_review_reason(state.failed_pages)
                policy.mark_record_stage_review(record, stage="validator", reason=reason)
                record.last_error = reason
                record.touch()
                storage_repository.save_state(self._engine)
            if corpus_workflow.finalize_loaded_pages(self._engine, record, self._ctx, active.paths):
                document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
                self._mark_terminal_record()
                return
            document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
            self._finalize_stage_failure(record)
            return
        self._sync_record_artifacts(content_hash)
        last_failed = state.failed_pages[-1] if state.failed_pages else None
        stage = last_failed.last_stage if last_failed is not None else stage_name_for_module("corpus_builder")
        if len(state.pages) == 1 and last_failed is not None:
            reason = f"{last_failed.last_error} (max {self._engine._max_failed_attempts} errors reached)"
        else:
            reason = "All pages failed permanently."
            if last_failed is not None and last_failed.last_error:
                reason = f"{reason} Last error: {last_failed.label}: {last_failed.last_error}"
        error_workflow.route_to_error(self._engine, record, self._ctx, stage=stage, reason=reason, final=True)
        document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
        self._mark_terminal_record()

    def _apply_page_review(self, page: PageWorkItem, result: PageStageResult) -> None:
        if not result.needs_review or not result.review_stage:
            return
        detail = result.review_reason or f"{page.label} needs review"
        policy.mark_record_stage_review(
            page.record,
            stage=result.review_stage,
            reason=detail,
        )
        log_detail = detail if page.page_total <= 1 else f"{page.label} -> {detail}"
        debug.append_log(
            self._engine,
            f"[{result.review_stage.upper()}-REVIEW] {page.record.relative_path}: {log_detail}",
        )
        page.record.touch()
        storage_repository.save_state(self._engine)

    def _sync_record_artifacts(self, content_hash: str, *, successful_only: bool = False) -> None:
        state = self._document_runs.get(content_hash)
        if state is None:
            return
        pages = state.succeeded_pages if successful_only else state.pages
        record = state.active.record
        record.artifacts.optimizer_raw_paths = [str(page.raw_path) for page in pages if page.raw_path]
        if not successful_only:
            page_images = list(state.page_image_paths)
        else:
            page_images = [
                state.page_image_paths[page.page_index]
                for page in pages
                if page.page_index < len(state.page_image_paths) and str(state.page_image_paths[page.page_index]).strip()
            ]
        record.artifacts.optimizer_page_image_paths = [str(path) for path in page_images if str(path).strip()]
        record.artifacts.interpreter_request_paths = [str(page.request_path) for page in pages if page.request_path]
        record.artifacts.interpreter_request_path = record.artifacts.interpreter_request_paths[0] if record.artifacts.interpreter_request_paths else ""
        record.artifacts.structured_paths = [str(page.structured_path) for page in pages if page.structured_path]
        record.artifacts.structured_path = record.artifacts.structured_paths[0] if record.artifacts.structured_paths else ""
        record.artifacts.validation_report_paths = [str(page.validation_path) for page in pages if page.validation_path]
        record.artifacts.validation_report_path = record.artifacts.validation_report_paths[0] if record.artifacts.validation_report_paths else ""
        record.artifacts.normalized_paths = [str(page.normalized_path) for page in pages if page.normalized_path]
        record.artifacts.normalized_path = record.artifacts.normalized_paths[0] if record.artifacts.normalized_paths else ""
        record.artifacts.normalizer_request_paths = [str(page.normalizer_request_path) for page in pages if page.normalizer_request_path]
        record.artifacts.normalizer_request_path = record.artifacts.normalizer_request_paths[0] if record.artifacts.normalizer_request_paths else ""
        record.touch()
        storage_repository.save_state(self._engine)

    def _finalize_stage_failure(self, record: Any) -> None:
        if record.final_disposition == "error":
            self._mark_terminal_record()
            return
        if record.status == "error":
            self._requeue_record(record)
            return
        self._mark_terminal_record()

    def _finalize_active_failure(self, active: document_workflow.ActiveRecordContext) -> None:
        document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
        self._finalize_stage_failure(active.record)

