from __future__ import annotations

import ingestion_layer_vision.orchestrator_contract as contract

from orchestrator_contract_support import DummyPluginManager, stub_extract
from .orchestrator_extract_document_support import _install_extract_common, _runtime_policy_path


def test_extract_document_returns_error_when_processor_yields_no_extracts(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    raw_output_path = tmp_path / "output" / "raw_extracts" / "source.raw.json"
    page_assets_dir = tmp_path / "output" / "page_assets" / "source.abcd1234"
    manager = DummyPluginManager({})

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            return None

        def process_single(self, *_args, **_kwargs):
            return []

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(page_assets_dir),
            "logical_source_path": "ingest/source.txt",
            "runtime_policy_path": str(_runtime_policy_path(tmp_path)),
        }
    )
    assert response == {"status": "error", "error": "Optimizer lieferte keine Raw-Extracts"}
    assert manager.calls == ["kill_all"]


def test_extract_document_returns_error_when_raw_path_missing(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    raw_output_path = tmp_path / "output" / "raw_extracts" / "source.raw.json"
    page_assets_dir = tmp_path / "output" / "page_assets" / "source.abcd1234"
    extract = stub_extract()
    manager = DummyPluginManager({})

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            return None

        def process_single(self, *_args, **_kwargs):
            return [extract]

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(page_assets_dir),
            "logical_source_path": "ingest/source.txt",
            "runtime_policy_path": str(_runtime_policy_path(tmp_path)),
        }
    )
    assert response == {"status": "error", "error": f"Raw-Extract fehlt nach Verarbeitung: {raw_output_path}"}
    assert manager.calls == ["kill_all"]


def test_extract_document_process_single_exception_returns_error(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    raw_output_path = tmp_path / "output" / "raw_extracts" / "source.raw.json"
    page_assets_dir = tmp_path / "output" / "page_assets" / "source.abcd1234"
    manager = DummyPluginManager({})

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            return None

        def process_single(self, *_args, **_kwargs):
            raise RuntimeError("processor exploded")

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(page_assets_dir),
            "logical_source_path": "ingest/source.txt",
            "runtime_policy_path": str(_runtime_policy_path(tmp_path)),
        }
    )
    assert response == {"status": "error", "error": "processor exploded"}
    assert manager.calls == ["kill_all"]
