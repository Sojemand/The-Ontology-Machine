"""Thread orchestration for the run stage scheduler."""

from __future__ import annotations

from collections import deque
import threading
from typing import Any

from .stage_scheduler_page_lifecycle import RunStageSchedulerPageLifecycle
from .stage_scheduler_state import DocumentPageRun, StageInbox
from .stage_scheduler_workers import RunStageSchedulerWorkers


class _RunStageScheduler(RunStageSchedulerWorkers, RunStageSchedulerPageLifecycle):
    def __init__(self, engine: Any, ctx: Any, records: list[Any]) -> None:
        self._engine = engine
        self._ctx = ctx
        self._pending_condition = threading.Condition()
        self._pending_records = deque(records)
        self._remaining = len(records)
        self._done = threading.Event()
        self._shutdown = False
        self._cancelled_exc: BaseException | None = None
        self._document_runs: dict[str, DocumentPageRun] = {}
        self._optimizer = StageInbox()
        self._request = StageInbox()
        self._interpreter = StageInbox()
        self._validator = StageInbox()
        self._normalizer = StageInbox()
        self._corpus = StageInbox()
        self._threads: list[threading.Thread] = []

    def run(self) -> None:
        if self._remaining <= 0:
            self._done.set()
            return
        self._threads = [
            threading.Thread(target=self._start_worker, name="orchestrator-start", daemon=True),
            threading.Thread(target=self._optimizer_worker, name="orchestrator-optimizer", daemon=True),
            threading.Thread(target=self._request_worker, name="orchestrator-request", daemon=True),
            threading.Thread(target=self._interpreter_worker, name="orchestrator-interpreter", daemon=True),
            threading.Thread(target=self._validator_worker, name="orchestrator-validator", daemon=True),
            threading.Thread(target=self._normalizer_worker, name="orchestrator-normalizer", daemon=True),
            threading.Thread(target=self._corpus_worker, name="orchestrator-corpus", daemon=True),
        ]
        for thread in self._threads:
            thread.start()
        self._done.wait()
        self._close()
        for thread in self._threads:
            thread.join()
        if self._cancelled_exc is not None:
            raise self._cancelled_exc

    def _next_record(self) -> Any | None:
        with self._pending_condition:
            while not self._shutdown and not self._pending_records:
                if self._remaining <= 0:
                    return None
                self._pending_condition.wait()
            if self._shutdown or not self._pending_records:
                return None
            return self._pending_records.popleft()

    def _requeue_record(self, record: Any) -> None:
        with self._pending_condition:
            if self._shutdown:
                return
            self._pending_records.append(record)
            self._pending_condition.notify_all()

    def _mark_terminal_record(self) -> None:
        with self._pending_condition:
            self._remaining = max(self._remaining - 1, 0)
            if self._remaining <= 0:
                self._done.set()
                self._shutdown = True
            self._pending_condition.notify_all()

    def _request_cancel(self, exc: BaseException) -> None:
        with self._pending_condition:
            if self._cancelled_exc is None:
                self._cancelled_exc = exc
            self._shutdown = True
            self._done.set()
            self._pending_condition.notify_all()
        self._close()

    def _close(self) -> None:
        self._optimizer.close()
        self._request.close()
        self._interpreter.close()
        self._validator.close()
        self._normalizer.close()
        self._corpus.close()


def run(engine: Any, ctx: Any, records: list[Any]) -> None:
    _RunStageScheduler(engine, ctx, records).run()
