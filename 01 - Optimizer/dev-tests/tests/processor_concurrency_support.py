"""Compatibility facade for processor concurrency test classes."""
from __future__ import annotations

from processor_callback_support import TestCallbackExceptionHandling, TestProcessSequentialCallbackFires
from processor_parallel_support import (
    TestConcurrentClaimOutputDir,
    TestConcurrentWriteExtractCollisionAvoidance,
    TestParallelCancelDuringProcessing,
    TestParallelWorkerException,
)
from processor_report_support import (
    TestReportCounterConsistency,
    TestReportLockProtectsConcurrentUpdates,
    TestRollbackExtractReport,
)

__all__ = [
    "TestCallbackExceptionHandling",
    "TestConcurrentClaimOutputDir",
    "TestConcurrentWriteExtractCollisionAvoidance",
    "TestParallelCancelDuringProcessing",
    "TestParallelWorkerException",
    "TestProcessSequentialCallbackFires",
    "TestReportCounterConsistency",
    "TestReportLockProtectsConcurrentUpdates",
    "TestRollbackExtractReport",
]
