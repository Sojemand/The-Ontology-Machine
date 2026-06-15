"""Concrete stage workers for the run stage scheduler."""

from __future__ import annotations

from ..integrations import stage_name_for_module
from . import (
    corpus_workflow,
    debug,
    document_types,
    document_workflow,
    error_workflow,
    interpreter_workflow,
    normalizer_workflow,
    optimizer_workflow,
    request_enrichment,
    request_enrichment_workflow,
    validator_workflow,
)
from .exceptions import OrchestratorCancelled
from .stage_scheduler_page_helpers import required_page_path
from .stage_scheduler_worker_loops import RunStageSchedulerWorkerLoops


class RunStageSchedulerWorkers(RunStageSchedulerWorkerLoops):
    def _start_worker(self) -> None:
        while True:
            record = self._next_record()
            if record is None:
                return
            active = None
            try:
                debug.check_cancelled(self._engine)
                active = document_workflow.start_record_attempt(self._engine, record, self._ctx)
                if active is None:
                    self._finalize_stage_failure(record)
                    continue
                if not self._optimizer.send(active):
                    document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
                    return
            except OrchestratorCancelled as exc:
                if active is not None:
                    document_workflow.cancel_record_attempt(self._engine, active, self._ctx, stage_name="Intake")
                    document_workflow.cleanup_attempt_runtime(self._engine, active, self._ctx)
                self._request_cancel(exc)
                return
            except Exception as exc:
                error_workflow.handle_failure(self._engine, record, self._ctx, record.last_stage or "Intake", f"Unexpected error: {exc}")
                self._finalize_stage_failure(record)
            finally:
                debug.set_active_document_log_path(self._engine, None)

    def _optimizer_worker(self) -> None:
        self._run_record_stage_worker(
            self._optimizer,
            stage_name_getter=lambda active: stage_name_for_module(active.record.optimizer_module_key or "optimizer"),
            execute=lambda active: optimizer_workflow.run_optimizer(self._engine, active.record, self._ctx, active.paths),
            on_success=self._on_optimizer_success,
        )

    def _request_worker(self) -> None:
        self._run_page_stage_worker(
            self._request,
            stage_key="request",
            stage_name=request_enrichment.REQUEST_ENRICHMENT_STAGE_NAME,
            execute=lambda page: request_enrichment_workflow.run_request_enrichment_page(
                self._engine,
                page.record,
                self._ctx,
                page.paths,
                page.raw_path,
                page_index=page.page_index,
                page_total=page.page_total,
            ),
            on_success=self._on_request_success,
        )

    def _interpreter_worker(self) -> None:
        self._run_page_stage_worker(
            self._interpreter,
            stage_key="interpreter",
            stage_name_getter=lambda page: stage_name_for_module(page.record.interpreter_module_key or "interpreter"),
            execute=lambda page: interpreter_workflow.run_interpreter_page(
                self._engine,
                page.record,
                self._ctx,
                page.paths,
                required_page_path(page.request_path, "Interpreter-Request"),
                page_index=page.page_index,
                page_total=page.page_total,
            ),
            on_success=self._on_interpreter_success,
        )

    def _validator_worker(self) -> None:
        self._run_page_stage_worker(
            self._validator,
            stage_key="validator",
            stage_name=stage_name_for_module("validator"),
            execute=lambda page: validator_workflow.run_validator_page(
                self._engine,
                page.record,
                self._ctx,
                page.paths,
                required_page_path(page.structured_path, "Structured-Output"),
                page.raw_path,
                page_index=page.page_index,
                page_total=page.page_total,
            ),
            on_success=self._on_validator_success,
        )

    def _normalizer_worker(self) -> None:
        self._run_page_stage_worker(
            self._normalizer,
            stage_key="normalizer",
            stage_name=stage_name_for_module("normalizer"),
            execute=lambda page: normalizer_workflow.run_normalizer_page(
                self._engine,
                page.record,
                self._ctx,
                page.paths,
                required_page_path(page.structured_path, "Structured-Output"),
                request_output_path=document_types.page_normalizer_request_path(page.paths, page.raw_path),
                page_index=page.page_index,
                page_total=page.page_total,
            ),
            on_success=self._on_normalizer_success,
        )

    def _corpus_worker(self) -> None:
        self._run_page_stage_worker(
            self._corpus,
            stage_key="corpus",
            stage_name=stage_name_for_module("corpus_builder"),
            execute=lambda page: corpus_workflow.load_page_into_corpus(
                self._engine,
                page.record,
                self._ctx,
                page.paths,
                page.raw_path,
                required_page_path(page.structured_path, "Structured-Output"),
                required_page_path(page.validation_path, "Validator-Report"),
                required_page_path(page.normalized_path, "Normalizer-Output"),
                page_index=page.page_index,
                page_total=page.page_total,
            ),
            on_success=self._on_corpus_success,
        )
