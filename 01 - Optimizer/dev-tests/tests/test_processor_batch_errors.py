from processor_test_support import TestProcessorErrors as _TestProcessorErrors


class TestProcessorBatchErrors:
    test_file_not_found = _TestProcessorErrors.test_file_not_found
    test_no_plugin_for_format = _TestProcessorErrors.test_no_plugin_for_format
    test_raw_extract_write_failure_is_recorded = _TestProcessorErrors.test_raw_extract_write_failure_is_recorded
    test_batch_required_llm_ocr_without_assets_is_recorded_as_failure = (
        _TestProcessorErrors.test_batch_required_llm_ocr_without_assets_is_recorded_as_failure
    )
