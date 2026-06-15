from __future__ import annotations

from pathlib import Path

from .edit_contract_support import _copy_module, _invoke_contract


def test_describe_surfaces_exposes_as_built_sections_and_owner_summary(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    payload = _invoke_contract(module_root, tmp_path, {"action": "describe_surfaces"})

    assert payload["status"] == "ok"
    assert payload["module_summary"].startswith("CORPUS BUILDER HELP")
    assert len(payload["summary_cards"]) == 4
    assert [card["label"] for card in payload["summary_cards"]] == [
        "Module Role",
        "Release State",
        "Search & Embeddings Readiness",
        "Capabilities & Boundaries",
    ]
    assert any(line.startswith("Published Release: semantic_release.default @") for line in payload["summary_cards"][1]["lines"])
    assert "Active Release: missing" in payload["summary_cards"][1]["lines"]
    assert "Debug Host Only: scan_debug_input, debug_run" in payload["summary_cards"][3]["lines"]
    assert "Embedding Model + state files: runtime-owned / read-only" in payload["summary_cards"][3]["lines"]

    descriptors = {item["surface_id"]: item for item in payload["surfaces"]}
    assert list(descriptors) == [
        "corpus_builder.settings",
        "corpus_builder.embeddings_policy",
        "corpus_builder.search_policy",
    ]
    assert descriptors["corpus_builder.settings"]["section"] == "Settings"
    assert descriptors["corpus_builder.embeddings_policy"]["section"] == "Settings"
    assert descriptors["corpus_builder.search_policy"]["section"] == "Settings"
    assert descriptors["corpus_builder.settings"]["field_groups"]
    assert descriptors["corpus_builder.embeddings_policy"]["field_groups"]
    assert descriptors["corpus_builder.search_policy"]["field_groups"]
    assert descriptors["corpus_builder.settings"]["render_actions_inline"] is False
    assert any(link["action"] == "preview_rebuild_from_artifacts" for link in descriptors["corpus_builder.settings"]["action_buttons"])
    assert any(link["action"] == "create_and_activate_new_corpus_db" for link in descriptors["corpus_builder.settings"]["action_buttons"])
    assert any(link["action"] == "create_and_rebuild_new_corpus_db" for link in descriptors["corpus_builder.settings"]["action_buttons"])
    rebuild_action = next(link for link in descriptors["corpus_builder.settings"]["action_buttons"] if link["action"] == "rebuild_from_artifacts")
    assert rebuild_action["show_progress_dialog"] is True
    assert "keine Embeddings" in rebuild_action["progress_warning"]
    assert any(link["action"] == "semantic_status" for link in descriptors["corpus_builder.settings"]["action_buttons"])
    assert any(link["action"] == "search" for link in descriptors["corpus_builder.search_policy"]["action_buttons"])
    export_action = next(link for link in descriptors["corpus_builder.search_policy"]["action_buttons"] if link["action"] == "export")
    export_db_input = next(field for field in export_action["inputs"] if field["name"] == "corpus_db_path")
    assert export_db_input["field_type"] == "open_file"
    embeddings_action = next(link for link in descriptors["corpus_builder.embeddings_policy"]["action_buttons"] if link["action"] == "generate_embeddings")
    embeddings_db_input = next(field for field in embeddings_action["inputs"] if field["name"] == "corpus_db_path")
    assert embeddings_db_input["field_type"] == "save_file"
    assert embeddings_action["runtime_owner"] == "orchestrator"
    assert embeddings_action["orchestrator_action"] == "embeddings"
    assert embeddings_action["show_progress_dialog"] is True
