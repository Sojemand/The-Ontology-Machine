from __future__ import annotations

import json
from pathlib import Path

from tests.pipeline_harness import create_source, error_case_root, load_single_record, make_engine, make_ui_state, runtime_files


def test_interpreter_error_freezes_debug_bundle_into_error_case(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    scenarios = {
        "doc.pdf": {
            "interpret": [
                {
                    "status": "error",
                    "error": "bad output",
                    "debug_payload": {"raw_provider_text": '{"confidence":"high"}', "failed_stage": "validate_model_output"},
                },
                {
                    "status": "error",
                    "error": "bad output",
                    "debug_payload": {"raw_provider_text": '{"confidence":"high"}', "failed_stage": "validate_model_output"},
                },
                {
                    "status": "error",
                    "error": "bad output",
                    "debug_payload": {"raw_provider_text": '{"confidence":"high"}', "failed_stage": "validate_model_output"},
                },
            ]
        }
    }

    summary = make_engine(tmp_path, scenarios).run(ui_state)
    record = load_single_record(tmp_path)
    debug_files = list((error_case_root(ui_state, "Interpreter") / "debug").glob("*.debug.json"))
    manifest = json.loads(Path(record.artifacts.bundle_manifest_path).read_text(encoding="utf-8"))

    assert summary.errors == 1
    assert record.final_disposition == "error"
    assert len(debug_files) == 1
    assert Path(record.artifacts.interpreter_debug_bundle_path) == debug_files[0]
    assert json.loads(debug_files[0].read_text(encoding="utf-8"))["failed_stage"] == "validate_model_output"
    assert manifest["artifacts"]["interpreter_debug_bundle_path"] == str(debug_files[0])
    assert runtime_files(tmp_path) == []

