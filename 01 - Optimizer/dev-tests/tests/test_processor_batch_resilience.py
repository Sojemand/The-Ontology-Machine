from processor_test_support import TestProcessorErrors as _TestProcessorErrors


class TestProcessorBatchResilience:
    test_render_failure_cleans_precreated_assets_in_batch_mode = (
        _TestProcessorErrors.test_render_failure_cleans_precreated_assets_in_batch_mode
    )
    test_sequential_process_survives_plugin_invoke_exception = (
        _TestProcessorErrors.test_sequential_process_survives_plugin_invoke_exception
    )
    test_sequential_process_survives_scan_detector_exception = (
        _TestProcessorErrors.test_sequential_process_survives_scan_detector_exception
    )
    test_sequential_process_survives_extract_build_exception = (
        _TestProcessorErrors.test_sequential_process_survives_extract_build_exception
    )

