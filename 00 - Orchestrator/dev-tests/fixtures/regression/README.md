# Regression Fixtures

Replay-based end-to-end regression cases for `00 - Orchestrator`.

- `happy_path`
  - Successful one-document run based on an anonymized one-page radiology
    finding with golden expectations for state, artifacts and `corpus.db`.
- `receipt_live`
  - Successful replay case based on a real live capture of a synthetic receipt
    with real sibling modules.
- `validator_fail`
  - Repeated Validator failure based on an anonymized one-page invoice, ending
    in a final Error Bundle after three attempts.
- `interpreter_review`
  - Synthetic Interpreter review case covering the early review/error path and
    retry logic.
- `normalizer_review`
  - Synthetic Normalizer review case covering three Normalizer retries and the
    final bundle with normalized artifact.
- `synthetic_scan_pdf_multipage`
  - Synthetic multipage scan-PDF case derived from production artifact shapes
    with page-scoped raw, request, structured, validation and normalized
    artifacts.
- `synthetic_born_digital_pdf_table`
  - Synthetic born-digital PDF table case for the `file` profile.
- `synthetic_docx_file_profile`
  - Synthetic DOCX case for the file-based document path.
- `synthetic_msg_thread_file_profile`
  - Synthetic MSG/email thread case with multiple page assets.
- `synthetic_text_file_profile`
  - Synthetic TXT case with multipage file-profile structure.
- `synthetic_png_vision_profile`
  - Synthetic PNG/raster-image case for the vision profile.
- Reset roundtrip
  - Tested in `test_pipeline_regression.py` intentionally from
    `validator_fail`, so reset removes only `Error Cases`, returns sources to
    Input and leaves successful artifacts plus `corpus.db` untouched.

Fixtures contain:

- `input/`
  - realistically named input files
- `replay/`
  - versioned stage artifacts such as `raw.json`, `structured.json`,
    `*.vision_validation_report.json`, `*.files_validation_report.json` and
    `normalized.json`
  - structure-preserving anonymized content, not a 1:1 copy of source documents
  - `synthetic_*` cases contain no production content and reproduce only
    format, profile, page-count and artifact-structure patterns
- `case.json`
  - stage scenario and golden expectations

The related tests live under:

```text
dev-tests/tests/test_pipeline_regression.py
```
