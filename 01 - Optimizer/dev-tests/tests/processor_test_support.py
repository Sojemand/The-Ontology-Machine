"""Stable facade for processor behavior test case groups."""
from processor_test_basic_cases import TestProcessorBasic, TestProcessorFilter
from processor_test_batch_error_cases import ProcessorBatchErrorCases
from processor_test_batch_resilience_cases import ProcessorBatchResilienceCases
from processor_test_output_cases import TestBlockFormattingParsing, TestNoArchiveOutput, TestProcessorCleanup
from processor_test_report_cases import TestProcessorCancel, TestProcessorReport
from processor_test_single_core_cases import ProcessSingleCoreCases
from processor_test_single_error_cases import ProcessSingleErrorCases
from processor_test_single_output_cases import ProcessSingleOutputCases
from processor_test_single_vision_output_cases import ProcessSingleVisionOutputCases
from processor_test_single_vision_pdf_cases import ProcessSingleVisionPdfCases


class TestProcessorErrors(ProcessorBatchErrorCases, ProcessorBatchResilienceCases):
    pass


class TestProcessSingle(
    ProcessSingleCoreCases,
    ProcessSingleOutputCases,
    ProcessSingleVisionOutputCases,
    ProcessSingleErrorCases,
    ProcessSingleVisionPdfCases,
):
    pass


__all__ = [
    "TestProcessorBasic",
    "TestProcessorFilter",
    "TestProcessorErrors",
    "TestProcessorCancel",
    "TestProcessorReport",
    "TestProcessSingle",
    "TestBlockFormattingParsing",
    "TestProcessorCleanup",
    "TestNoArchiveOutput",
]
