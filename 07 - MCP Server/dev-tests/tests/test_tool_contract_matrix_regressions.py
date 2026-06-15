from __future__ import annotations

from pathlib import Path
from typing import Any
import pytest
from mcp_server import support_monitor
from mcp_server.tools import ToolFailure, call_tool
from tests.tool_contract_matrix_fixtures import *
from tests.tool_contract_matrix_helpers import _write_empty_sqlite
from tests.tool_contract_matrix_recorder import OwnerCallRecorder
@pytest.mark.parametrize(
    ("tool_name", "arguments", "message"),
    [
        ("describe_owner_surfaces", {}, "module fehlt"),
        ("inspect_pipeline", {}, "Unbekanntes Tool"),
        ("support_incident_workflow", {}, "Unbekanntes Tool"),
        ("manage_runtime_settings", {}, "Unbekanntes Tool"),
        ("manage_credentials", {}, "Unbekanntes Tool"),
        ("list_support_incidents", {"limit": 0}, "limit muss eine positive Ganzzahl"),
        ("assess_support_incident", {}, "classification fehlt"),
        ("assess_support_incident", {"classification": "unexpected_exception"}, "reportable assessments require incident_id or event/module_key payload"),
        ("preview_support_bug_report", {}, "assessment_id fehlt"),
        ("queue_support_bug_report", {}, "assessment_id fehlt"),
        ("dismiss_support_incident", {}, "incident_id fehlt"),
        ("describe_owner_surfaces", {"module": "corpus_builder"}, "module muss eines"),
        ("read_owner_surface", {"module": "orchestrator"}, "surface_id fehlt"),
        ("corpus_builder.describe_surfaces", {"surface_id": "corpus_builder.settings"}, "akzeptiert keine Argumente"),
        ("corpus_builder.read_surface", {}, "surface_id fehlt"),
        ("corpus_builder.validate_surface", {"surface_id": "corpus_builder.settings", "value": []}, "value muss ein Objekt"),
        ("corpus_builder.write_surface", {"surface_id": "corpus_builder.settings", "value": []}, "value muss ein Objekt"),
        ("validate_owner_surface", {"module": "normalizer", "surface_id": "normalizer.release", "value": []}, "value muss ein Objekt"),
        ("normalizer_source_action", {"action": "create_zero_shot_working_release"}, "Unbekanntes Tool"),
        ("check_working_release_readiness", {"language": "german"}, "Unbekanntes Tool"),
        ("create_working_release_package", {"artifact_folder": "x", "default_runtime_locale": "german"}, "default_runtime_locale muss ein gueltiger Locale-Code"),
        ("create_locale_scaffold", {"target_locale": "fr"}, "artifact_folder fehlt"),
        ("create_locale_scaffold", {"artifact_folder": "x", "source_locale": "en"}, "target_locale fehlt"),
        ("create_locale_scaffold", {"artifact_folder": "x", "source_locale": "en", "target_locale": "fr", "overwrite_existing": "yes"}, "overwrite_existing muss ein Bool"),
        ("inspect_source_document_sample", {}, "source_document_path fehlt"),
        ("inspect_source_document_sample", {"source_document_path": "x", "max_excerpt_chars": 0}, "max_excerpt_chars muss eine positive Ganzzahl"),
        ("inspect_source_document_sample", {"source_document_path": "x", "cleanup_days": -1}, "cleanup_days muss eine nicht-negative Ganzzahl"),
        ("review_source_document_taxonomy_coverage", {}, "source_document_path fehlt"),
        ("review_source_document_taxonomy_coverage", {"source_document_path": "x", "max_excerpt_chars": 0}, "max_excerpt_chars muss eine positive Ganzzahl"),
        ("export_default_blueprint_release", {"blueprint_ref": "default"}, "output_path fehlt"),
        ("create_minimal_custom_release", {"language": "de"}, "artifact_folder fehlt"),
        (
            "create_minimal_custom_release",
            {
                "artifact_folder": "x",
                "language": "de",
                "projection_id": "fantasy.story.custom.v1",
                "archive_label": "Fantasy",
                "archive_description": "Fantasy archive",
                "document_types": [],
                "field_codes": [{"code": "character", "label": "Character"}],
            },
            "document_types darf nicht leer sein",
        ),
        ("broaden_custom_release", {"artifact_folder": "x"}, "Unbekanntes Tool"),
        ("create_projection_draft", {"projection_id": "x"}, "artifact_folder fehlt"),
        ("generate_locale_translation_payload", {"source_language": "de", "target_language": "en", "model": "gpt-test", "max_output_tokens": 0}, "max_output_tokens muss eine positive Ganzzahl"),
        ("read_translation_glossary", {}, "locale fehlt"),
        ("read_translation_glossary", {"locale": "german"}, "locale muss ein gueltiger Locale-Code"),
        ("upsert_translation_glossary_entry", {"locale": "de", "english_term": "invoice"}, "canonical fehlt"),
        ("upsert_translation_glossary_entry", {"locale": "de", "english_term": "   ", "canonical": "Rechnung"}, "english_term fehlt"),
        ("upsert_translation_glossary_entry", {"locale": "de", "english_term": "invoice", "canonical": "Rechnung", "aliases": "Beleg"}, "aliases muss eine String-Liste"),
        ("remove_translation_glossary_entry", {"locale": "de"}, "english_term fehlt"),
        ("create_new_corpus_from_blueprint", {}, "Unbekanntes Tool"),
        ("create_pipeline_workspace_db", {}, "Unbekanntes Tool"),
        ("create_empty_corpus_db", {"corpus_db_path": "x", "artifact_folder": "y"}, "kennt diese Argumente"),
        ("prepare_pipeline_workspace_root", {}, "artifact_folder fehlt"),
        ("prepare_pipeline_workspace_root", {"artifact_folder": "x", "database_name": "db"}, "kennt diese Argumente"),
        ("create_pipeline_workspace_from_working_release", {"artifact_folder": "x", "database_name": "db"}, "Unbekanntes Tool"),
        ("activate_working_release_on_workspace_db", {"artifact_folder": "x", "database_name": "db"}, "Unbekanntes Tool"),
        ("reset_workspace_db_and_activate_working_release", {"artifact_folder": "x"}, "Unbekanntes Tool"),
        ("verify_workspace_active_release", {"artifact_folder": "x", "database_name": "db"}, "language fehlt"),
        ("verify_workspace_active_release", {"artifact_folder": "x", "database_name": "db", "language": "en", "projection_ids": "story"}, "projection_ids muss eine String-Liste"),
        ("write_workspace_release_change_confirmation", {}, "artifact_folder fehlt"),
        ("write_workspace_release_change_confirmation", {"artifact_folder": "x", "database_name": "db", "activation_preflight_result": [], "activation_decision": "activate_only", "confirm_release_change": True}, "activation_preflight_result muss ein Objekt"),
        (
            "write_workspace_release_change_confirmation",
            {
                "artifact_folder": "x",
                "database_name": "db",
                "activation_preflight_result": {},
                "activation_decision": "reset",
                "confirm_release_change": True,
            },
            "activation_decision muss",
        ),
        ("plan_custom_release_revision", {"artifact_folder": "x", "database_name": "db"}, "Unbekanntes Tool"),
        ("read_revision_candidate_release", {}, "release_path fehlt"),
        ("inspect_release_revision_context", {}, "corpus_db_path fehlt"),
        ("classify_release_revision", {"candidate_release": {}}, "database_state fehlt"),
        ("write_workspace_db_reset_confirmation", {"artifact_folder": "x", "database_name": "db"}, "confirm_reset fehlt"),
        (
            "write_workspace_db_reset_confirmation",
            {"artifact_folder": "x", "database_name": "db", "confirm_reset": True},
            "reset_reason fehlt",
        ),
        ("run_active_pipeline", {"mode": "all"}, "mode muss"),
        ("run_active_pipeline", {"max_input_preview": 0}, "max_input_preview muss eine positive Ganzzahl"),
        ("start_active_pipeline_run", {"mode": "all"}, "mode muss"),
        ("start_active_pipeline_run", {"max_input_preview": 0}, "max_input_preview muss eine positive Ganzzahl"),
        ("inspect_active_pipeline_run", {"log_tail_lines": 0}, "log_tail_lines muss eine positive Ganzzahl"),
        ("cancel_active_pipeline_run", {"timeout_seconds": 0}, "timeout_seconds muss eine positive Ganzzahl"),
        ("preview_active_corpus_source_reimport", {"max_preview": 0}, "max_preview muss eine positive Ganzzahl"),
        ("prepare_active_corpus_source_reimport", {}, "user_confirmed fehlt"),
        ("prepare_active_corpus_source_reimport", {"user_confirmed": False}, "user_confirmed muss true"),
        ("reset_active_corpus_db", {}, "confirmation_artifact_path fehlt"),
        ("load_semantic_release", {}, "release_path fehlt"),
        ("activation_preflight", {}, "release_path fehlt"),
        ("build_and_activate_release_for_active_corpus", {"target_locale": "de"}, "Unbekanntes Tool"),
        ("create_new_corpus_from_release", {"release_path": "x"}, "Unbekanntes Tool"),
        ("backfill_stale", {"document_ids": ["doc-1", 2]}, "document_ids muss eine String-Liste"),
        ("backfill_stale", {"limit": 0}, "limit muss eine positive Ganzzahl"),
        ("merge_preflight", {"source_db_path": "x"}, "target_db_path fehlt"),
        ("merge_corpora", {"target_db_path": "x"}, "source_db_path fehlt"),
        ("rebuild_corpus_from_artifacts", {"replace_existing": "yes"}, "replace_existing muss ein Bool"),
        ("create_and_rebuild_new_corpus_db", {}, "Unbekanntes Tool"),
        ("generate_embeddings", {"corpus_db_path": "x"}, "runtime_model fehlt"),
        ("search_corpus", {"query": "invoice", "limit": False}, "limit muss eine positive Ganzzahl"),
        ("search_corpus", {}, "query fehlt"),
        ("export_corpus", {"output_path": "x", "include_archived": "yes"}, "include_archived muss ein Bool"),
        ("validator.read_surface", {}, "surface_id fehlt"),
        ("validator.validate_surface", {"surface_id": "validator.settings", "value": []}, "value muss ein Objekt"),
        ("validator.write_surface", {"surface_id": "validator.settings", "value": {}, "module": "validator"}, "kennt diese Argumente"),
        ("inspect_runtime", {"unexpected": True}, "akzeptiert keine Argumente"),
        ("write_runtime_settings", {"settings": []}, "settings muss ein Objekt"),
        ("set_runtime_api_key", {"target": "llm_shared"}, "secret_value fehlt"),
        ("delete_runtime_api_key", {}, "target fehlt"),
        ("reveal_secret", {"target": "llm_shared", "purpose": "test"}, "unlock_phrase fehlt"),
    ],
)
def test_mcp_tool_regressions_reject_bad_arguments(
    tool_name: str, arguments: dict[str, Any], message: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = OwnerCallRecorder({})
    recorder.install(monkeypatch)
    monkeypatch.setattr(support_monitor, "state_root", lambda: tmp_path / "support")

    with pytest.raises(ToolFailure, match=message):
        call_tool(tool_name, arguments)

    assert recorder.product_calls == []
    assert recorder.edit_calls == []
    assert recorder.admin_calls == []


def test_context_activation_rejects_missing_db_before_owner_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    recorder = OwnerCallRecorder({})
    recorder.install(monkeypatch)

    with pytest.raises(ToolFailure, match="corpus_db_path existiert nicht"):
        call_tool("activate_corpus_context", {"corpus_db_path": str(corpus_root / "missing.db")})

    assert recorder.product_calls == []


def test_context_activation_rejects_db_outside_declared_storage(
    mcp_files: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    recorder = OwnerCallRecorder(mcp_files)
    recorder.install(monkeypatch)

    with pytest.raises(ToolFailure, match="muss innerhalb von corpus_output_folder liegen"):
        call_tool(
            "activate_corpus_context",
            {"corpus_db_path": mcp_files["active_db"], "corpus_output_folder": str(outside)},
        )

    assert recorder.product_calls == []


def test_create_empty_corpus_rejects_existing_sqlite_sidecars(
    mcp_files: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    wal_path = Path(mcp_files["fresh_db"]).with_name(f"{Path(mcp_files['fresh_db']).name}-wal")
    wal_path.write_text("leftover wal", encoding="utf-8")
    recorder = OwnerCallRecorder(mcp_files)
    recorder.install(monkeypatch)

    with pytest.raises(ToolFailure, match="corpus_db_path existiert bereits"):
        call_tool(
            "create_empty_corpus_db",
            {"corpus_db_path": mcp_files["fresh_db"], "corpus_output_folder": mcp_files["corpus_root"]},
        )

    assert recorder.product_calls == []
