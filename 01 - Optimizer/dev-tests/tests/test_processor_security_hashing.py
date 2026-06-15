from processor_security_support import (
    test_archive_dir_from_malformed_hash_is_sanitized_via_recompute,
    test_content_hash_already_valid_no_double_prefix,
    test_content_hash_invalid_non_hex_is_recomputed,
    test_content_hash_raw_hex_gets_prefix,
    test_process_file_invalid_hash_and_recompute_failure_records_error,
)

