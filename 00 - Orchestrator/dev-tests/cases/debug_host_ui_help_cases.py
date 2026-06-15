from __future__ import annotations

from orchestrator.ui import debug_help, debug_view_support


def test_optimizer_help_mentions_processed_hashes_and_vram_limits() -> None:
    title, body = debug_help.get_help("optimizer") or ("", "")

    assert title == "Optimizer Debug Guide"
    assert "merged Optimizer" in body
    assert "scan/image and pageable-file profiles" in body
    assert "Preview which supported source files" in body
    assert "dispatches internally by profile" in body


def test_interpreter_help_texts_document_runtime_injections() -> None:
    title, body = debug_help.get_help("interpreter") or ("", "")

    assert title == "Interpreter Debug Guide"
    assert "max_output_tokens" in body
    assert "Request Enrichment" in body
    assert "projection_catalog" in body
    assert "outputs/requests/.../interpreter.request.json" in body
    assert "context.interpreter_profile" in body
    assert "optimizer:debug_run -> Request Enrichment -> interpreter:debug_run" in body


def test_validator_help_text_describes_structured_input_and_raw_evidence() -> None:
    title, body = debug_help.get_help("validator") or ("", "")

    assert title == "Validator Debug Guide"
    assert "*.structured.json" in body
    assert "Raw JSON" in body
    assert "Raw Folder" in body
    assert "processing.interpreter_profile = file" in body
    assert "`vision` does not need raw" in body
    assert "fails closed" in body
    assert "config_snapshot.json" in body
    assert "report_index.json" in body
    assert "*.structured.normalized.json" in body


def test_set_row_visible_tracks_real_widget_visibility() -> None:
    class Row:
        def pack(self, **_kwargs) -> None:
            return None

        def pack_forget(self) -> None:
            return None

    row = Row()
    debug_view_support.set_row_visible(row, True)
    assert row.visible is True
    debug_view_support.set_row_visible(row, False)
    assert row.visible is False
