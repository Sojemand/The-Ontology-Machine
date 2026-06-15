from processor_test_support import TestProcessSingle as _TestProcessSingle


class TestProcessSingleCore:
    test_process_single_returns_extracts = _TestProcessSingle.test_process_single_returns_extracts
    test_non_vision_paths_unchanged_by_ocr_hardening = (
        _TestProcessSingle.test_non_vision_paths_unchanged_by_ocr_hardening
    )
    test_process_single_writes_output = _TestProcessSingle.test_process_single_writes_output
    test_process_single_write_output_requires_output_target = (
        _TestProcessSingle.test_process_single_write_output_requires_output_target
    )
    test_process_single_uses_hash_suffix_for_existing_output_name = (
        _TestProcessSingle.test_process_single_uses_hash_suffix_for_existing_output_name
    )
    test_process_single_uses_child_run_directory_when_output_is_active = (
        _TestProcessSingle.test_process_single_uses_child_run_directory_when_output_is_active
    )
    test_process_single_dry_run = _TestProcessSingle.test_process_single_dry_run
    test_process_single_to_dict = _TestProcessSingle.test_process_single_to_dict

