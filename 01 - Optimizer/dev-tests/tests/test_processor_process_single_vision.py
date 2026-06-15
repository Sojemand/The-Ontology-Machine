from processor_test_support import TestProcessSingle as _TestProcessSingle


class TestProcessSingleVision:
    test_process_single_vision_dry_run_requires_output_with_explicit_output_dir = (
        _TestProcessSingle.test_process_single_vision_dry_run_requires_output_with_explicit_output_dir
    )
    test_process_single_vision_dry_run_requires_output_with_requested_output_dir = (
        _TestProcessSingle.test_process_single_vision_dry_run_requires_output_with_requested_output_dir
    )
    test_process_single_vision_same_basenames_get_isolated_page_assets = (
        _TestProcessSingle.test_process_single_vision_same_basenames_get_isolated_page_assets
    )
    test_process_single_render_failure_cleans_precreated_asset_dir = (
        _TestProcessSingle.test_process_single_render_failure_cleans_precreated_asset_dir
    )
    test_process_single_empty_render_result_is_error_and_cleans_output = (
        _TestProcessSingle.test_process_single_empty_render_result_is_error_and_cleans_output
    )
    test_vision_pdf_writes_single_extract_for_multi_page_scan = (
        _TestProcessSingle.test_vision_pdf_writes_single_extract_for_multi_page_scan
    )
    test_parallel_vision_same_basenames_keep_isolated_page_assets = (
        _TestProcessSingle.test_parallel_vision_same_basenames_keep_isolated_page_assets
    )

