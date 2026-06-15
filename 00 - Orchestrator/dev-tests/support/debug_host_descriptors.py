from __future__ import annotations

from orchestrator.debug_host.types import DebugDescriptor


ROW_KEYS = (
    "input_path",
    "source_path",
    "format",
    "doc_type",
    "max_size_mb",
    "batch_size",
    "worker_count",
    "raw_path",
    "raw_root",
    "persist_page_images",
    "check_toggles",
    "hash_tools",
)


def descriptors() -> dict[str, DebugDescriptor]:
    return {
        "optimizer": descriptor(
            "optimizer",
            "Optimizer",
            controls=("mode", "filters", "worker_count", "hash_tools"),
            artifacts=("raw_extracts", "page_assets"),
            supports_batch=True,
            supports_scan=True,
        ),
        "interpreter": descriptor(
            "interpreter",
            "Interpreter",
            stage_role="Interpreter",
            artifacts=("interpreter_request", "structured_output"),
            supports_batch=True,
            supports_scan=True,
        ),
        "validator": descriptor(
            "validator",
            "Validator",
            stage_role="Validator",
            controls=("mode", "raw_evidence", "check_toggles"),
            artifacts=("validation_reports", "config_snapshot", "report_index"),
            supports_batch=True,
            input_source="module_selected_input",
        ),
        "normalizer": descriptor(
            "normalizer",
            "Normalizer",
            stage_role="Normalizer",
            controls=("mode", "worker_count"),
            artifacts=("normalized_outputs",),
            supports_batch=True,
            input_source="module_selected_input",
        ),
        "corpus_builder": descriptor(
            "corpus_builder",
            "Corpus Builder Vision",
            stage_role="Corpus Builder",
            controls=("mode", "persist_page_images"),
            artifacts=("corpus_db", "preview_report", "load_report"),
            supports_batch=True,
            supports_scan=True,
            input_source="module_selected_input",
        ),
    }


def descriptor(
    module_key: str,
    display_name: str,
    *,
    stage_role: str = "Optimizer",
    controls: tuple[str, ...] = (),
    artifacts: tuple[str, ...] = (),
    supports_batch: bool = False,
    supports_scan: bool = False,
    input_source: str = "orchestrator_main_input",
) -> DebugDescriptor:
    return DebugDescriptor(
        module_key=module_key,
        display_name=display_name,
        stage_role=stage_role,
        supports_batch=supports_batch,
        supports_single=True,
        supports_scan=supports_scan,
        input_source=input_source,
        output_source="orchestrator_assigned_output",
        controls=controls,
        artifacts=artifacts,
    )
