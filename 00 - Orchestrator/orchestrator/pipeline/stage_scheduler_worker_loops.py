"""Generic worker loops used by the run stage scheduler."""

from __future__ import annotations

from typing import Callable

from . import debug, document_workflow, error_workflow
from .exceptions import OrchestratorCancelled
from .page_stage_types import PageStageResult, PageWorkItem
from .stage_scheduler_state import StageInbox


class RunStageSchedulerWorkerLoops:
    def _run_record_stage_worker(
        self,
        inbox: StageInbox,
        *,
        stage_name_getter: Callable[[document_workflow.ActiveRecordContext], str],
        execute: Callable[[document_workflow.ActiveRecordContext], object],
        on_success: Callable[[document_workflow.ActiveRecordContext, object], None],
    ) -> None:
        while True:
            active = inbox.receive()
            if active is None:
                return
            debug.set_active_document_log_path(self._engine, active.paths.working_log_path)
            try:
                result = execute(active)
                if result is None or result is False:
                    self._finalize_active_failure(active)
                    continue
                on_success(active, result)
            except OrchestratorCancelled as exc:
                document_workflow.cancel_record_attempt(self._engine, active, self._ctx, stage_name=stage_name_getter(active))
                document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
                self._request_cancel(exc)
                return
            except Exception as exc:
                error_workflow.handle_failure(
                    self._engine,
                    active.record,
                    self._ctx,
                    stage_name_getter(active),
                    f"Unexpected error: {exc}",
                )
                self._finalize_active_failure(active)
            finally:
                debug.set_active_document_log_path(self._engine, None)
                inbox.complete()

    def _run_page_stage_worker(
        self,
        inbox: StageInbox,
        *,
        stage_key: str,
        execute: Callable[[PageWorkItem], PageStageResult],
        on_success: Callable[[PageWorkItem, PageStageResult], None],
        stage_name: str | None = None,
        stage_name_getter: Callable[[PageWorkItem], str] | None = None,
    ) -> None:
        while True:
            page = inbox.receive()
            if page is None:
                return
            debug.set_active_document_log_path(self._engine, page.paths.working_log_path)
            resolved_stage_name = stage_name_getter(page) if stage_name_getter is not None else str(stage_name or stage_key)
            try:
                debug.check_cancelled(self._engine)
                result = execute(page)
                if not result.ok:
                    self._handle_page_failure(page, result, stage_key=stage_key, stage_name=resolved_stage_name)
                    continue
                on_success(page, result)
            except OrchestratorCancelled as exc:
                document_workflow.cancel_record_attempt(self._engine, page.active, self._ctx, stage_name=resolved_stage_name)
                document_workflow.cleanup_attempt_runtime(self._engine, page.active, self._ctx)
                self._request_cancel(exc)
                return
            except Exception as exc:
                self._handle_page_failure(
                    page,
                    PageStageResult.failure(f"Unexpected error: {exc}"),
                    stage_key=stage_key,
                    stage_name=resolved_stage_name,
                )
            finally:
                debug.set_active_document_log_path(self._engine, None)
                inbox.complete()
