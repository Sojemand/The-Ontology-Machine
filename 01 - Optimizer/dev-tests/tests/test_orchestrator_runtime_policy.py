from __future__ import annotations

import json
import sys
from pathlib import Path

import ingestion_layer_vision.orchestrator_contract as contract

from orchestrator_contract_support import DummyPluginManager, runtime_policy_payload, stub_extract

PIPELINE_ROOT = Path(__file__).resolve().parents[3]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from tools.phase4_locale_test_support import build_locale_runtime_artifacts


def _install_extract_common(monkeypatch, manager, processor_cls) -> None:
    monkeypatch.setattr(contract, "load_config", lambda _path: object())
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(contract, "Processor", processor_cls)


def test_extract_document_requires_runtime_policy_path(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    manager = DummyPluginManager({})

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Processor darf ohne runtime_policy_path nicht gebaut werden")

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(tmp_path / "out.raw.json"),
            "page_assets_dir": str(tmp_path / "pages"),
            "logical_source_path": "ingest/source.txt",
        }
    )
    assert response == {"status": "error", "error": "runtime_policy_path fehlt."}
    assert manager.calls == []


def test_extract_document_rejects_invalid_runtime_policy_bundle(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    runtime_policy_path = tmp_path / "runtime_semantic_assets.json"
    runtime_policy_path.write_text("{}", encoding="utf-8")
    manager = DummyPluginManager({})

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Processor darf bei ungueltigem Runtime-Bundle nicht gebaut werden")

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(tmp_path / "out.raw.json"),
            "page_assets_dir": str(tmp_path / "pages"),
            "logical_source_path": "ingest/source.txt",
            "runtime_policy_path": str(runtime_policy_path),
        }
    )
    assert response["status"] == "error"
    assert "runtime_semantic_assets" in response["error"]
    assert manager.calls == []


def test_extract_document_passes_loaded_runtime_policy_state_into_processor(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    runtime_policy_path = tmp_path / "runtime_semantic_assets.json"
    expected_policy = runtime_policy_payload()
    runtime_policy_path.write_text(json.dumps(expected_policy), encoding="utf-8")
    raw_output_path = tmp_path / "output" / "raw_extracts" / "source.raw.json"
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text("{}", encoding="utf-8")
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}
    extract = stub_extract()

    class DummyProcessor:
        def __init__(self, *_args, **kwargs):
            captured["runtime_policy_state"] = kwargs["runtime_policy_state"]

        def process_single(self, *_args, **_kwargs):
            return [extract]

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(tmp_path / "pages"),
            "logical_source_path": "ingest/source.txt",
            "runtime_policy_path": str(runtime_policy_path),
        }
    )
    state = captured["runtime_policy_state"]
    assert response["status"] == "ok"
    assert state.release_fingerprint == expected_policy["release_fingerprint"]
    assert state.bundle_version == expected_policy["vision_policy_bundle"]["bundle_version"]
    assert state.ocr_policy.policy_version == expected_policy["vision_policy_bundle"]["ocr_policy"]["policy_version"]
    assert not hasattr(state, "semantic_extraction_policy")
    assert manager.calls == ["kill_all"]


def test_extract_document_accepts_real_locale_specific_runtime_policy_bundle(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    runtime_policy_path = tmp_path / "runtime_semantic_assets.en.json"
    _project_root, _release, expected_policy = build_locale_runtime_artifacts(tmp_path, runtime_locale="en")
    expected_policy["vision_policy_bundle"].pop("semantic_extraction_policy", None)
    expected_policy["vision_policy_bundle"]["ocr_policy"].pop("projection_overrides", None)
    runtime_policy_path.write_text(json.dumps(expected_policy), encoding="utf-8")
    raw_output_path = tmp_path / "output" / "raw_extracts" / "source.raw.json"
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text("{}", encoding="utf-8")
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}
    extract = stub_extract()

    class DummyProcessor:
        def __init__(self, *_args, **kwargs):
            captured["runtime_policy_state"] = kwargs["runtime_policy_state"]

        def process_single(self, *_args, **_kwargs):
            return [extract]

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(tmp_path / "pages"),
            "logical_source_path": "ingest/source.txt",
            "runtime_policy_path": str(runtime_policy_path),
        }
    )
    state = captured["runtime_policy_state"]
    assert response["status"] == "ok"
    assert expected_policy["runtime_locale"] == "en"
    assert expected_policy["projection_catalog"]["runtime_locale"] == "en"
    assert state.release_fingerprint == expected_policy["release_fingerprint"]
    assert manager.calls == ["kill_all"]
