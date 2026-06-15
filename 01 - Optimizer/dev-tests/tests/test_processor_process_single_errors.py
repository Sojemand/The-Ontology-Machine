from processor_test_support import TestProcessSingle as _TestProcessSingle


class TestProcessSingleErrors:
    test_process_single_file_not_found = _TestProcessSingle.test_process_single_file_not_found
    test_process_single_file_too_large = _TestProcessSingle.test_process_single_file_too_large
    test_process_single_unsupported_format = _TestProcessSingle.test_process_single_unsupported_format
    test_process_single_plugin_exception_is_wrapped_as_plugin_error = (
        _TestProcessSingle.test_process_single_plugin_exception_is_wrapped_as_plugin_error
    )
    test_process_single_required_llm_ocr_without_output_dir_raises_value_error = (
        _TestProcessSingle.test_process_single_required_llm_ocr_without_output_dir_raises_value_error
    )
