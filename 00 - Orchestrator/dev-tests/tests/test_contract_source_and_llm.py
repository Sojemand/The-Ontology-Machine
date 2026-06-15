from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from orchestrator.orchestrator_contract import source_inspection_runtime
from orchestrator.pipeline import path_budget

from .contract_test_support import _run_contract, contract_module


def test_source_inspection_filename_is_budgeted_against_state_parent() -> None:
    parent = Path(
        "C:/Users/Norma/Workspace/The Ontology Machine/00 - Orchestrator/"
        "state/source_inspections/inspect_123456789abc/Input"
    )
    source_name = f"0001_{'very-long-source-name-' * 10}.pdf"

    name = source_inspection_runtime.safe_inspection_filename(source_name, parent=parent)

    assert name.endswith(".pdf")
    assert len(str(parent / name)) <= path_budget.WINDOWS_PATH_BUDGET
    assert len(name) < len(source_name)


def test_contract_inspect_source_document_sample_runs_optimizer_debug(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "Fantasy Story.txt"
    source.write_text("The moonlit tower watched the vanished prince.", encoding="utf-8")
    starts: list[dict] = []
    monkeypatch.setattr(contract_module, "ORCHESTRATOR_ROOT", tmp_path)

    def fake_start(module_key, mode, input_root, *, source_path, state_root, session_id, options, modules):
        starts.append(
            {
                "module_key": module_key,
                "mode": mode,
                "input_root": Path(input_root),
                "source_path": source_path,
                "state_root": Path(state_root),
                "session_id": session_id,
                "options": dict(options),
                "modules": modules,
            }
        )
        session_root = Path(state_root) / "debug_sessions" / session_id / module_key
        raw_path = session_root / "outputs" / "raw_extracts" / "Fantasy_Story.raw.json"
        raw_path.parent.mkdir(parents=True)
        raw_path.write_text(
            json.dumps(
                    {
                        "schema_version": "optimizer_raw_v2",
                        "optimizer_profile": "file",
                        "source": {
                            "file_name": "Fantasy Story.txt",
                            "file_path": "Fantasy Story.txt",
                            "document_type": "story",
                            "language": "en",
                            "page_count": 1,
                        },
                        "extraction": {"plugin_name": "fake", "plugin_version": "1.0.0", "processing_time_ms": 1},
                        "metadata": {},
                        "context": {"document_page_count": 1},
                        "ocr_reference": {
                            "blocks": [
                                {
                                    "id": "para_1",
                                    "type": "paragraph",
                                    "value": "The moonlit tower watched the vanished prince.",
                                    "value_type": "text",
                                    "layout_label": "Opening Scene",
                                    "position": {"page": 1},
                                }
                            ]
                        },
                    }
                ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            active_step=None,
            session_root=session_root,
            result=SimpleNamespace(
                status="ok",
                summary="1 file processed",
                error="",
                outputs={"raw_extracts": ["outputs/raw_extracts/Fantasy_Story.raw.json"], "page_images": []},
            ),
        )

    monkeypatch.setattr(contract_module.workflow.source_inspection.debug_workflow, "start", fake_start)

    payload = _run_contract(
        tmp_path,
        {
            "action": "inspect_source_document_sample",
            "source_document_path": str(source),
            "max_excerpt_chars": 500,
        },
    )

    assert payload["status"] == "ok"
    assert payload["signals"]["filename"] == "Fantasy Story.txt"
    assert payload["signals"]["detected_language"] == "en"
    assert payload["excerpt"]["truncated"] is False
    assert "moonlit tower" in "\n".join(payload["excerpt"]["chunks"])
    assert "Opening Scene" in payload["content_hints"]["headings"]
    assert payload["output_refs"]["raw_extract_paths"] == payload["raw_extract_paths"]
    assert Path(payload["input_copy_path"]).exists()
    assert starts[0]["module_key"] == "optimizer"
    assert starts[0]["mode"] == "single"
    assert starts[0]["source_path"] == "Fantasy_Story.txt"
    assert starts[0]["options"] == {"worker_count": 1}
    assert starts[0]["modules"] is not None

def test_kernel_llm_runtime_profile_dispatches(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        contract_module.kernel_llm,
        "runtime_profile_action",
        lambda *, root: {
            "status": "ok",
            "output_refs": {"runtime_settings": {"semantic_control_kernel_llm": {"model": "gpt-test", "max_output_tokens": 8000}}},
        },
    )

    payload = _run_contract(tmp_path, {"action": "kernel_llm_runtime_profile"})

    assert payload["status"] == "ok"
    assert payload["output_refs"]["runtime_settings"]["semantic_control_kernel_llm"]["model"] == "gpt-test"

def test_kernel_llm_generate_uses_interpreter_runtime_credentials(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    class Settings:
        def runtime_settings_for(self, module_key: str, operation: str = ""):
            assert module_key == "interpreter"
            return {"model": "gpt-test", "max_output_tokens": 8000}

    context = SimpleNamespace(ready=True, env_overlay={"VISION_PROVIDER_API_KEY": "secret"})
    monkeypatch.setattr(contract_module.kernel_llm, "load_runtime_settings", lambda _state_dir: Settings())
    monkeypatch.setattr(contract_module.kernel_llm.credentials, "resolve_runtime_credentials", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(contract_module.kernel_llm, "resolve_module_runtime", lambda *_args, **_kwargs: SimpleNamespace(key="interpreter"))

    def fake_invoke(spec, payload, *, timeout, env_overlay):
        captured["spec"] = spec
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["env_overlay"] = env_overlay
        return {
            "status": "ok",
            "output_refs": {
                "llm_response": {
                    "provider": "dummy",
                    "model": "gpt-test",
                    "response_id": "r1",
                    "status": "complete",
                    "output_text": "{}",
                    "raw_provider_response_ref": {},
                    "usage": {},
                }
            },
        }

    monkeypatch.setattr(contract_module.kernel_llm.module_adapter, "invoke_contract", fake_invoke)

    result = contract_module.kernel_llm.generate_action(
        {
            "llm_provider_request": {
                "messages": [{"role": "user", "content": "Return JSON"}],
                "target_schema": {"type": "object"},
                "max_output_tokens": 123,
            }
        },
        root=tmp_path,
    )

    assert result["status"] == "ok"
    assert captured["payload"]["action"] == "generate_llm"
    assert captured["payload"]["runtime_settings"] == {"model": "gpt-test", "max_output_tokens": 8000}
    assert captured["payload"]["max_output_tokens"] == 123
    assert captured["env_overlay"] == {"VISION_PROVIDER_API_KEY": "secret"}
    assert "VISION_PROVIDER_API_KEY" not in json.dumps(captured["payload"])
