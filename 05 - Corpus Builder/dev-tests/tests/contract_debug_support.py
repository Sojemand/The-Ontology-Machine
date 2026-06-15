from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.context import ModuleContext
from corpus_builder.models.serialization import atomic_json_write
from corpus_builder.orchestrator_contract import validation, workflow
from corpus_builder.services import build_load_bundle, load_batch
from tests.fixtures.semantic_context import make_semantic_context
from .semantic_release_test_support import build_release_variant


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def dispatch(context: ModuleContext, payload: dict) -> dict:
    return workflow.dispatch(
        payload,
        context=context,
        require_action_fn=validation.require_action,
        parse_activate_semantic_release_command_fn=validation.parse_activate_semantic_release_command,
        parse_create_and_activate_new_corpus_db_command_fn=validation.parse_create_and_activate_new_corpus_db_command,
        parse_activation_preflight_command_fn=validation.parse_activation_preflight_command,
        parse_debug_run_command_fn=validation.parse_debug_run_command,
        parse_generate_embeddings_command_fn=validation.parse_generate_embeddings_command,
        parse_healthcheck_command_fn=validation.parse_healthcheck_command,
        parse_load_document_command_fn=validation.parse_load_document_command,
        parse_scan_debug_input_command_fn=validation.parse_scan_debug_input_command,
        parse_semantic_status_command_fn=validation.parse_semantic_status_command,
        parse_read_active_semantic_release_command_fn=validation.parse_read_active_semantic_release_command,
        parse_load_semantic_release_command_fn=validation.parse_load_semantic_release_command,
        parse_semantic_audit_command_fn=validation.parse_semantic_audit_command,
        parse_backfill_stale_command_fn=validation.parse_backfill_stale_command,
        parse_merge_preflight_command_fn=validation.parse_merge_preflight_command,
        parse_merge_corpus_databases_command_fn=validation.parse_merge_corpus_databases_command,
        parse_search_command_fn=validation.parse_search_command,
        parse_stats_command_fn=validation.parse_stats_command,
        parse_export_command_fn=validation.parse_export_command,
        parse_preview_rebuild_from_artifacts_command_fn=validation.parse_preview_rebuild_from_artifacts_command,
        parse_rebuild_from_artifacts_command_fn=validation.parse_rebuild_from_artifacts_command,
        parse_create_and_rebuild_new_corpus_db_command_fn=validation.parse_create_and_rebuild_new_corpus_db_command,
    )


def write_active_release(context: ModuleContext, projection_id: str = "housing.default.v1") -> None:
    context.ensure_runtime_dirs()
    atomic_json_write(context.config_path, {"database": {"corpus_db": "./output/corpus.db"}})
    payload = build_release_variant(project_root=PROJECT_ROOT, projection_ids=[projection_id])
    context.semantic_release_state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_pipeline_record(
    pipeline_root: Path,
    *,
    base_name: str,
    vision_structured: dict,
    vision_validation_report: dict,
    vision_normalized: dict,
    subdir: str = "finance",
) -> Path:
    normalized_dir = pipeline_root / "normalized" / subdir
    structured_dir = pipeline_root / "structured" / subdir
    validation_dir = pipeline_root / "validation" / subdir
    normalized_path = normalized_dir / f"{base_name}.structured.normalized.json"
    write_json(normalized_path, vision_normalized)
    write_json(structured_dir / f"{base_name}.structured.json", vision_structured)
    write_json(validation_dir / f"{base_name}.vision_validation_report.json", vision_validation_report)
    return normalized_path


def loaded_semantic_corpus(
    tmp_path: Path,
    *,
    vision_structured: dict,
    vision_validation_report: dict,
    vision_normalized: dict,
) -> tuple[ModuleContext, Path]:
    context = make_semantic_context(tmp_path)
    corpus_db_path = tmp_path / "corpus.db"
    structured_path = tmp_path / "invoice.structured.json"
    validation_path = tmp_path / "invoice.vision_validation_report.json"
    normalized_path = tmp_path / "invoice.structured.normalized.json"
    write_json(structured_path, vision_structured)
    write_json(validation_path, vision_validation_report)
    write_json(normalized_path, vision_normalized)

    bundle = build_load_bundle(
        context,
        normalized_path=normalized_path,
        structured_path=structured_path,
        validation_path=validation_path,
        corpus_db_path=corpus_db_path,
    )
    result = load_batch(context, [bundle])

    assert result.loaded == 1
    assert corpus_db_path.exists()
    return context, corpus_db_path
