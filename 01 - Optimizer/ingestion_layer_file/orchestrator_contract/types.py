"""Action constants for the Optimizer subprocess contract."""

CLASSIFY_DOCUMENT_ACTION = "classify_document"
DEBUG_RUN_ACTION = "debug_run"
EXTRACT_DOCUMENT_ACTION = "extract_document"
HEALTHCHECK_ACTION = "healthcheck"
HEALTHCHECK_PIPELINE_RUN_SCOPE = "pipeline_run"
DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS = 30
PIPELINE_RUN_HEALTHCHECK_TIMEOUT_SECONDS = 10
SCAN_DEBUG_INPUT_ACTION = "scan_debug_input"
HEALTHCHECK_DEPENDENCIES = (
    "pdf-pymupdf",
    "docx-python",
    "odt-odfpy",
    "rtf-reader",
    "mail-rfc822",
    "mail-outlook-msg",
    "mail-outlook-store",
    "renderer-pdf",
    "renderer-office",
    "renderer-html",
)

__all__ = [
    "CLASSIFY_DOCUMENT_ACTION",
    "DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS",
    "DEBUG_RUN_ACTION",
    "EXTRACT_DOCUMENT_ACTION",
    "HEALTHCHECK_ACTION",
    "HEALTHCHECK_DEPENDENCIES",
    "HEALTHCHECK_PIPELINE_RUN_SCOPE",
    "PIPELINE_RUN_HEALTHCHECK_TIMEOUT_SECONDS",
    "SCAN_DEBUG_INPUT_ACTION",
]

