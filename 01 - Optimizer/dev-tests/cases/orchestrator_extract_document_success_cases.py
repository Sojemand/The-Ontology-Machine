from __future__ import annotations

import ingestion_layer_vision.orchestrator_contract as contract
from ingestion_layer_vision.processor import policy as processor_policy

from orchestrator_contract_support import DummyPluginManager, stub_extract
from .orchestrator_extract_document_support import _install_extract_common, _runtime_policy_path


def test_extract_document_passes_explicit_targets_into_processor(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    logical_path = "kunden/vision/logical/source.txt"
    raw_output_path = tmp_path / "output" / "raw_extracts" / "source.raw.json"
    page_assets_dir = tmp_path / "output" / "page_assets" / "source.abcd1234"
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text("{}", encoding="utf-8")
    extract = stub_extract(ingest_id="12345678-1234-1234-1234-123456789abc")
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            return None

        def process_single(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return [extract]

    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(page_assets_dir),
            "logical_source_path": logical_path,
            "runtime_policy_path": str(_runtime_policy_path(tmp_path)),
        }
    )
    assert response["status"] == "ok"
    assert response["document_raw_path"] == str(raw_output_path)
    assert captured["args"] == (source,)
    assert captured["kwargs"] == {
        "write_output": True,
        "raw_output_path": raw_output_path,
        "page_assets_dir": page_assets_dir,
        "logical_source_path": logical_path,
    }
    assert manager.calls == ["kill_all"]


def test_extract_document_returns_budgeted_page_raw_paths_for_multi_page_outputs(tmp_path, monkeypatch) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"%PDF-1.4 fake")
    raw_output_path = tmp_path / "output" / "raw_extracts" / "scan.raw.json"
    page_assets_dir = tmp_path / "output" / "page_assets" / "scan.abcd1234"
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text("{}", encoding="utf-8")
    page_extracts = [
        stub_extract(),
        type("PageExtract", (), {"page_number": 1})(),
        type("PageExtract", (), {"page_number": 2})(),
    ]
    expected_page_paths = processor_policy.page_raw_output_paths(raw_output_path, 2)
    for page_path in expected_page_paths:
        page_path.write_text("{}", encoding="utf-8")

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            return None

        def process_single(self, *_args, **_kwargs):
            return page_extracts

    manager = DummyPluginManager({})
    _install_extract_common(monkeypatch, manager, DummyProcessor)
    response = contract._extract_document(
        {
            "source_path": str(source),
            "raw_output_path": str(raw_output_path),
            "page_assets_dir": str(page_assets_dir),
            "logical_source_path": "queue/scan.pdf",
            "runtime_policy_path": str(_runtime_policy_path(tmp_path)),
        }
    )

    assert response["status"] == "ok"
    assert response["page_raw_paths"] == [str(path) for path in expected_page_paths]
    assert manager.calls == ["kill_all"]
