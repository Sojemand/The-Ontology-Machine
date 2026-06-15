"""Success-stage handlers for the orchestrator stage scheduler."""

from __future__ import annotations

from . import document_workflow
from .page_stage_types import PageStageResult, PageWorkItem
from .stage_scheduler_page_helpers import record_debug_path
from .stage_scheduler_state import DocumentPageRun


class RunStageSchedulerSuccessHandlers:
    def _on_optimizer_success(self, active: document_workflow.ActiveRecordContext, result: object) -> None:
        active.raw_paths = list(result)
        if not active.raw_paths:
            self._finalize_active_failure(active)
            return
        page_total = len(active.raw_paths)
        pages = [
            PageWorkItem(active=active, page_index=index, page_total=page_total, raw_path=raw_path)
            for index, raw_path in enumerate(active.raw_paths)
        ]
        self._document_runs[active.record.content_hash] = DocumentPageRun(
            active=active,
            pages=pages,
            page_image_paths=list(getattr(active.record.artifacts, "optimizer_page_image_paths", []) or []),
        )
        self._sync_record_artifacts(active.record.content_hash)
        for page in pages:
            if not self._request.send(page):
                document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
                return

    def _on_request_success(self, page: PageWorkItem, result: PageStageResult) -> None:
        page.request_path = result.path
        self._sync_record_artifacts(page.record.content_hash)
        if not self._interpreter.send(page):
            document_workflow.cleanup_attempt_runtime(self._engine, page.active, self._ctx)

    def _on_interpreter_success(self, page: PageWorkItem, result: PageStageResult) -> None:
        page.structured_path = result.path
        page.interpreter_debug_bundle_path = record_debug_path(page.record)
        self._apply_page_review(page, result)
        self._sync_record_artifacts(page.record.content_hash)
        if not self._validator.send(page):
            document_workflow.cleanup_attempt_runtime(self._engine, page.active, self._ctx)

    def _on_validator_success(self, page: PageWorkItem, result: PageStageResult) -> None:
        page.validation_path = result.path
        self._apply_page_review(page, result)
        self._sync_record_artifacts(page.record.content_hash)
        if not self._normalizer.send(page):
            document_workflow.cleanup_attempt_runtime(self._engine, page.active, self._ctx)

    def _on_normalizer_success(self, page: PageWorkItem, result: PageStageResult) -> None:
        page.normalized_path = result.path
        page.normalizer_request_path = result.request_path
        self._apply_page_review(page, result)
        self._sync_record_artifacts(page.record.content_hash)
        if not self._corpus.send(page):
            document_workflow.cleanup_attempt_runtime(self._engine, page.active, self._ctx)

    def _on_corpus_success(self, page: PageWorkItem, _result: PageStageResult) -> None:
        page.terminal = True
        page.succeeded = True
        state = self._document_runs.get(page.record.content_hash)
        if state is not None and page not in state.succeeded_pages:
            state.succeeded_pages.append(page)
        self._sync_record_artifacts(page.record.content_hash)
        self._finalize_document_if_complete(page.record.content_hash)


