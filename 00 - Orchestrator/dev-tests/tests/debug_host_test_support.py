from __future__ import annotations

import json
from pathlib import Path


def write_debug_registry(
    tmp_path: Path,
    *,
    controls: tuple[str, ...] = ("mode", "filters", "worker_count", "hash_tools"),
    include_validator: bool = False,
    include_normalizer: bool = False,
    include_interpreter: bool = False,
    include_corpus_builder: bool = False,
) -> Path:
    write_debug_module(tmp_path / "01 - Optimizer", "optimizer", "Optimizer", controls=controls)
    modules = {
        "optimizer": {"path": "./01 - Optimizer"},
    }
    if include_interpreter:
        write_debug_module(
            tmp_path / "02 - Interpreter",
            "interpreter",
            "Interpreter",
            actions=["interpret_document", "healthcheck", "debug_run"],
            controls=(),
            artifacts=("interpreter_request", "structured_output"),
            supports_batch=True,
            supports_scan=True,
        )
        modules["interpreter"] = {"path": "./02 - Interpreter"}
    if include_validator:
        write_debug_module(
            tmp_path / "03 - Validator",
            "validator",
            "Validator",
            actions=["validate_document", "healthcheck", "debug_run"],
            controls=("mode", "raw_evidence", "check_toggles"),
            artifacts=("validation_reports", "config_snapshot", "report_index"),
            supports_batch=True,
            supports_scan=False,
            input_source="module_selected_input",
        )
        modules["validator"] = {"path": "./03 - Validator"}
    if include_normalizer:
        write_debug_module(
            tmp_path / "04 - Normalizer",
            "normalizer",
            "Normalizer",
            actions=["normalize_document", "build_projection_catalog", "build_runtime_semantic_assets", "healthcheck", "debug_run"],
            controls=("mode", "worker_count"),
            artifacts=("normalized_outputs",),
            supports_batch=True,
            supports_scan=False,
            input_source="module_selected_input",
        )
        modules["normalizer"] = {"path": "./04 - Normalizer"}
    if include_corpus_builder:
        write_debug_module(
            tmp_path / "05 - Corpus Builder",
            "corpus_builder",
            "Corpus Builder Vision",
            actions=["load_document", "activate_semantic_release", "read_active_semantic_release", "generate_embeddings", "healthcheck", "scan_debug_input", "debug_run"],
            controls=("mode", "persist_page_images"),
            artifacts=("corpus_db", "preview_report", "load_report"),
            supports_batch=True,
            supports_scan=True,
            input_source="module_selected_input",
        )
        modules["corpus_builder"] = {"path": "./05 - Corpus Builder"}
    registry_path = tmp_path / "module-registry.json"
    registry_path.write_text(json.dumps({"modules": modules}), encoding="utf-8")
    return registry_path


def write_debug_module(
    module_root: Path,
    module_key: str,
    display_name: str,
    *,
    controls: tuple[str, ...] = ("mode", "filters", "worker_count", "hash_tools"),
    actions: list[str] | None = None,
    artifacts: tuple[str, ...] = ("raw_extracts", "page_assets"),
    supports_batch: bool = True,
    supports_scan: bool = True,
    input_source: str = "orchestrator_main_input",
) -> None:
    runtime_dir = module_root / "runtime" / "python"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "python.exe").write_text("", encoding="utf-8")
    manifest = {
        "module_key": module_key,
        "display_name": display_name,
        "contract_version": 1,
        "runtime_dir": "runtime/python",
        "contract_module": "ingestion_layer_vision.orchestrator_contract",
        "launcher_module": "ingestion_layer_vision",
        "actions": actions or ["extract_document", "healthcheck", "scan_debug_input", "debug_run"],
        "external_dependencies": [],
    }
    if actions is None:
        manifest["debug_surface"] = {
            "supports_batch": True,
            "supports_single": True,
            "supports_scan": True,
            "input_source": input_source,
            "output_source": "orchestrator_assigned_output",
            "controls": list(controls),
            "artifacts": ["raw_extracts", "page_assets"],
        }
    elif "debug_run" in actions:
        manifest["debug_surface"] = {
            "supports_batch": supports_batch,
            "supports_single": True,
            "supports_scan": supports_scan,
            "input_source": input_source,
            "output_source": "orchestrator_assigned_output",
            "controls": list(controls),
            "artifacts": list(artifacts),
        }
    (module_root / "module-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

